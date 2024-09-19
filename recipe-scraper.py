from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import re
import spacy
from setup_database import create_pool, insert_recipe

nlp = spacy.load('en_core_web_sm')

async def get_page_letter(browser):
    link = "https://www.food.com/browse/allrecipes/?page=1&letter=123"

    page = await browser.new_page()
    await page.goto(link)
    
    magic_columns = page.locator('//div[@class="letter-filters magic-buttons"]/ul/li[contains(@class, "magic-columns-3")]')
    magic_columns_count = await magic_columns.count()
    letters = []
    for i in range(magic_columns_count):
        li_element = magic_columns.nth(i)
        ul_element = li_element.locator('ul')
        li_count = await ul_element.locator('li').count()
        for j in range(li_count):
            inner_li_element = ul_element.locator('li').nth(j)
            li_class = await inner_li_element.get_attribute('class')
            if li_class == 'selected':
                letter = await inner_li_element.inner_html()
            else:
                letter = await inner_li_element.locator('a').inner_text()
            letters.append(letter)
    await page.close()
    return letters

async def get_recipe_links(browser, letters, pool):
    for letter in letters:
        page_url = f"https://www.food.com/browse/allrecipes/?page=1&letter={letter}"
        page = await browser.new_page()
        await page.goto(page_url)
        last_page = int(await page.locator('//li[@class="page  page-last  js-paging-after"]/a').inner_text())
        await page.close()
        
        tasks = []
        max_concurrent_scraping_tasks = 30
        semaphore = asyncio.Semaphore(max_concurrent_scraping_tasks)

        for page in range(1, last_page + 1):
            base_url = f"https://www.food.com/browse/allrecipes/?page={page}&letter={letter}"
            link = base_url.format(page=page, letter=letter)
                        
            page = await browser.new_page()
            await page.goto(link)
            recipe_section = page.locator('//div[@class="content-columns"]')
            tabs_count = await recipe_section.locator('div').count()
            for tab in range(tabs_count):
                ul_section = recipe_section.locator('div').nth(tab).locator('ul')
                li_count = await ul_section.locator('li').count()
                for li in range(li_count):
                    links = ul_section.locator('li').nth(li).locator('a')
                    for recipe_link in await links.element_handles():
                        r_link = await recipe_link.get_attribute('href')
                        task = asyncio.create_task(get_recipe_data(semaphore, browser, r_link, pool))
                        tasks.append(task)
            await page.close()
    await asyncio.gather(*tasks)

async def get_recipe_data(semaphore, browser, recipe_link, pool):
    async with semaphore:
        base_url = "https://www.food.com"
        link = base_url + recipe_link
        page = await browser.new_page()
        await page.goto(link)
        await page.wait_for_load_state("domcontentloaded")

        try:
            if "Whoops…" in await page.content():
                return
            recipe_name = await page.locator('//*[@id="recipe"]/div[2]/h1').inner_text()
            # print(recipe_name)
            category = await page.locator('//*[@id="recipe"]/div[1]/nav/ol/li[2]/a/span').inner_text()
            raw_preparation_time = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[1]/dd').inner_text()
            preparation_time = preparation_time_to_minutes(raw_preparation_time)
            number_of_ingredients = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[2]/dd').inner_text()
            # print(f"Number of ingredients: {number_of_ingredients}")

            if await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dt').inner_text() == 'Yields:':
                if await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dd').count() > 0:
                    number_of_servings = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dd').inner_text()
                else:
                    number_of_servings = 'N/A'
            elif await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dt').inner_text() == 'Serves:' or await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dt').inner_text() == 'Serves:':
                number_of_servings = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dd').inner_text()
            else:
                number_of_servings = 'N/A'
            # print(f"Number of servings: {number_of_servings}")
            
            if await page.locator('//*[@id="recipe"]/div[3]/div/div/a/span/div/span').count() > 0:
                number_of_ratings = await page.locator('//*[@id="recipe"]/div[3]/div/div/a/span/div/span').inner_text()
            else:
                number_of_ratings = 0
                
            number_of_steps = await page.locator('//*[@id="recipe"]/section[2]/ul/li').count()
            # print(f"Number of steps: {number_of_steps}")
            
            # print(f"Number of ratings: {number_of_ratings}")
            ingredients_list = []
            current_heading = None
            ingredient_items = page.locator('//*[@id="recipe"]/section[1]/ul/li')
            item_count = await ingredient_items.count()
            for i in range(item_count):
                li_element = ingredient_items.nth(i)
                if await li_element.locator('h4').count() > 0:
                    current_heading = (await li_element.locator('h4').inner_text()).strip()
                    continue
                
                ingredient_text = await li_element.inner_text()
                ingredient_text = ingredient_text.replace('\n', ' ').strip()
                # clean_ingredient = get_main_ingredient(ingredient_text)
                # print(f"Cleaned ingredient: {clean_ingredient}")
                ingredients_list.append({
                    'heading': current_heading,
                    'ingredient_text': ingredient_text
                    #'clean_ingredient': clean_ingredient
                })
            recipe_data = {
                'recipe_name': recipe_name,
                'number_of_ingredients': number_of_ingredients,
                'number_of_steps': number_of_steps,
                'number_of_servings': number_of_servings,
                'preparation_time': preparation_time,
                'ingredients_list': ingredients_list,
                'number_of_ratings': number_of_ratings,
                'recipe_link': link
            }
            await insert_recipe(pool, recipe_data)
        except Exception as e:
            print(e)
            return
        finally:
            await page.close()
        
def preparation_time_to_minutes(raw_preparation_time):
    preparation_time = 0
    hours_match = re.search(r'(\d+)\s*hr', raw_preparation_time)
    minutes_match = re.search(r'(\d+)\s*min', raw_preparation_time)
    if hours_match:
        hours = int(hours_match.group(1)) * 60
        preparation_time += hours
    if minutes_match:
        minutes = int(minutes_match.group(1))
        preparation_time += minutes
    return preparation_time

async def get_main_ingredient(ingredient):
    unwanted_terms = [
    'teaspoon', 'tablespoon', 'cup', 'ounce', 'pound', 'lb', 'lbs', 'g', 'kg', 'ml', 'liter', 
    'pinch', 'dash', 'amount', 'optional', 'or', 'fresh', 'large', 'medium', 'small', 
    'whole', 'favorite', 'clove', 'grated', 'stalks', 'boiling'
    ]
    
    # Remove fractions and special characters like "⁄" or "/"
    ingredient = re.sub(r'[⁄/]', '', ingredient)
    
    # Remove numbers and fractions (e.g., 1/2)
    ingredient = re.sub(r'\d+\/\d+|\d+', '', ingredient)

    # Tokenize the cleaned ingredient using Spacy
    doc = nlp(ingredient)
    
    # Filter out unwanted terms and measurement units
    filtered_tokens = []
    
    for token in doc:
        # Skip unwanted terms
        if token.lemma_ in unwanted_terms or token.pos_ in ['DET', 'NUM']:
            continue
        # Capture the main noun phrases (consecutive nouns or noun + adjectives)
        if token.pos_ in ["NOUN", "PROPN", "ADJ"]:
            filtered_tokens.append(token.text)
    
    # Join the cleaned tokens back into a single string
    cleaned_ingredient = " ".join(filtered_tokens)
    
    return cleaned_ingredient.strip()
    
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        pool = await create_pool()
        letters = await get_page_letter(browser=browser)
        await get_recipe_links(browser=browser, letters=letters, pool=pool)
        await pool.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
