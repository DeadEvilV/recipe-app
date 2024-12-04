from playwright.async_api import async_playwright
import asyncio
import pandas as pd
import re
import spacy
from setup_database import create_pool, insert_recipe
import json
import os

nlp = spacy.load('en_core_web_sm')

STATE_FILE = 'scraping_state.json'

def load_state(state_file=STATE_FILE):
    """Load the scraping state from a JSON file."""
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            return json.load(f)
    else:
        return {'letter': None, 'page': 0}

def save_state(state, state_file=STATE_FILE):
    """Save the scraping state to a JSON file."""
    with open(state_file, 'w') as f:
        json.dump(state, f)

async def get_page_letter(page_queue):
    link = "https://www.food.com/browse/allrecipes/?page=1&letter=123"

    page = await page_queue.get()
    await page.goto(link)
    await page.wait_for_load_state("domcontentloaded")

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
    await page_queue.put(page)
    return letters

async def get_recipe_links(browser, letters, pool, state, page_queue):
    max_concurrent_scraping_tasks = 30
    semaphore = asyncio.Semaphore(max_concurrent_scraping_tasks)
    for letter in letters:
        if state['letter'] is not None:
            if letter < state['letter']:
                continue
            elif letter == state['letter']:
                start_page = state['page'] + 1
            else:
                start_page = 1
        else:
            start_page = 1

        page_url = f"https://www.food.com/browse/allrecipes/?page=1&letter={letter}"
        page = await page_queue.get()
        await page.goto(page_url)
        await page.wait_for_load_state("domcontentloaded")
        last_page = int(await page.locator('//li[@class="page  page-last  js-paging-after"]/a').inner_text())
        await page_queue.put(page)

        for page_num in range(start_page, last_page + 1):
            tasks = []
            base_url = f"https://www.food.com/browse/allrecipes/?page={page_num}&letter={letter}"
            link = base_url.format(page_num=page_num, letter=letter)
                        
            page = await page_queue.get()
            await page.goto(link)
            await page.wait_for_load_state("domcontentloaded")
            recipe_section = page.locator('//div[@class="content-columns"]')
            tabs_count = await recipe_section.locator('div').count()
            for tab in range(tabs_count):
                ul_section = recipe_section.locator('div').nth(tab).locator('ul')
                li_count = await ul_section.locator('li').count()
                for li in range(li_count):
                    links = ul_section.locator('li').nth(li).locator('a')
                    for recipe_link in await links.element_handles():
                        r_link = await recipe_link.get_attribute('href')
                        task = asyncio.create_task(get_recipe_data(semaphore, browser, r_link, pool, page_queue))
                        tasks.append(task)
            await page_queue.put(page)
            if tasks:
                await asyncio.gather(*tasks)
                state['letter'] = letter
                state['page'] = page_num
                save_state(state)

async def get_recipe_data(semaphore, browser, recipe_link, pool, page_queue):
    async with semaphore:
        base_url = "https://www.food.com"
        link = base_url + recipe_link
        page = await page_queue.get()
        page.set_default_timeout(30000)
        await page.goto(link)
        await page.wait_for_load_state("domcontentloaded")

        try:
            if "Whoops…" in await page.content():
                return
            recipe_name = await page.locator('//*[@id="recipe"]/div[2]/h1').inner_text()
            if await page.locator('//*[@id="recipe"]/div[1]/nav/ol/li[2]/a/span').count() > 0:
                category = await page.locator('//*[@id="recipe"]/div[1]/nav/ol/li[2]/a/span').inner_text()
            else:
                category = "Unknown"
            raw_preparation_time = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[1]/dd').inner_text()
            preparation_time = preparation_time_to_minutes(raw_preparation_time)
            number_of_ingredients = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[2]/dd').inner_text()
            
            page.set_default_timeout(5000)
            number_of_servings = 'N/A'
            if await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dt').inner_text() == 'Serves:':
                if await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dd').count() > 0:
                    number_of_servings = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dd').inner_text()
                elif await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dd/div/span').count() > 0:
                    number_of_servings = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dd/div/span').inner_text()
            elif await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dt').inner_text() == 'Serves:':
                if await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[3]/dd').count() > 0:
                    number_of_servings = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dd').inner_text()
                elif await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dd/div/span').count() > 0:
                    number_of_servings = await page.locator('//*[@id="recipe"]/div[9]/div/dl/div[4]/dd/div/span').inner_text()
            page.set_default_timeout(30000)
            if await page.locator('//*[@id="recipe"]/div[3]/div/div/a/span/div/span').count() > 0:
                number_of_ratings = await page.locator('//*[@id="recipe"]/div[3]/div/div/a/span/div/span').inner_text()
            else:
                number_of_ratings = 0
                
            number_of_steps = await page.locator('//*[@id="recipe"]/section[2]/ul/li').count()

            direction_dict = {}
            for step in range(number_of_steps):
                direction = await page.locator('//*[@id="recipe"]/section[2]/ul/li').nth(step).inner_text()
                direction_dict[step + 1] = direction
            
            ingredients_list = []
            current_heading = None
            ingredient_items = page.locator('//*[@id="recipe"]/section[1]/ul/li')
            item_count = await ingredient_items.count()
            clean_ingredients = []
            for i in range(item_count):
                li_element = ingredient_items.nth(i)
                if await li_element.locator('h4').count() > 0:
                    current_heading = (await li_element.locator('h4').inner_text()).strip()
                    continue
                
                ingredient_text = await li_element.inner_text()
                ingredient_text = ingredient_text.replace('\n', ' ').strip()
                clean_ingredient = get_main_ingredient(ingredient_text)
                clean_ingredients.append(clean_ingredient)
                ingredients_list.append({
                    'heading': current_heading,
                    'ingredient_text': ingredient_text
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
            await insert_recipe(pool, recipe_data, direction_dict, clean_ingredients, category)
        except Exception as e:
            print(e)
            return
        finally:
            await page_queue.put(page)
        
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

def get_main_ingredient(ingredient):
    ingredient = re.sub(r'\(.*?\)', '', ingredient)
    
    ingredient = re.sub(r'[⁄/]', '', ingredient)
    
    ingredient = ingredient.strip("-–— ")
    
    units_list = [
        'teaspoon', 'teaspoons', 'tsp', 'tablespoon', 'tablespoons', 'tbsp', 'cup', 'cups',
        'pint', 'pints', 'quart', 'quarts', 'gallon', 'gallons', 'ounce', 'ounces', 'oz',
        'pound', 'pounds', 'lb', 'lbs', 'gram', 'grams', 'g', 'kg', 'kilogram', 'kilograms',
        'milliliter', 'milliliters', 'ml', 'liter', 'liters', 'l', 'pinch', 'dash',
        'can', 'cans', 'package', 'packages', 'pkg', 'bottle', 'bottles', 'jar', 'jars',
        'slice', 'slices', 'clove', 'cloves', 'stalk', 'stalks', 'head', 'heads', 'inch',
        'inches', 'strip', 'strips', 'piece', 'pieces', 'bag', 'bags', 'envelope', 'envelopes',
        'box', 'boxes', 'container', 'containers', 'bulb', 'bulbs'
    ]
    units = r'(' + '|'.join(units_list) + r')'
    numbers = r'(\d+\s*\d*\/?\d*|\d*\/\d+|\d+)'
    patterns = [
        r'^\s*[-–—]?\s*' + numbers + r'\s*' + units + r'\b\s*',
        r'^\s*[-–—]?\s*' + numbers + r'\b\s*',
        r'^\s*[-–—]?\s*' + units + r'\b\s*',
    ]
    for pattern in patterns:
        ingredient = re.sub(pattern, '', ingredient, flags=re.IGNORECASE)
    
    ingredient = re.sub(r'\b\d+\b', '', ingredient)
    
    unwanted_terms = [
        'teaspoon', 'teaspoons', 'tsp', 'tablespoon', 'tablespoons', 'tbsp', 'cup', 'cups',
        'pint', 'pints', 'quart', 'quarts', 'gallon', 'gallons', 'ounce', 'ounces', 'oz',
        'pound', 'pounds', 'lb', 'lbs', 'gram', 'grams', 'g', 'kg', 'kilogram', 'kilograms',
        'milliliter', 'milliliters', 'ml', 'liter', 'liters', 'l', 'pinch', 'dash',
        'can', 'cans', 'package', 'packages', 'pkg', 'bottle', 'bottles', 'jar', 'jars',
        'slice', 'slices', 'clove', 'cloves', 'stalk', 'stalks', 'head', 'heads', 'inch',
        'inches', 'strip', 'strips', 'piece', 'pieces', 'bag', 'bags', 'envelope', 'envelopes',
        'box', 'boxes', 'container', 'containers', 'bulb', 'bulbs', 'fresh', 'large', 'medium',
        'small', 'extra', 'packed', 'finely', 'coarsely', 'roughly', 'chopped', 'minced',
        'grated', 'diced', 'sliced', 'ground', 'boneless', 'skinless', 'lean', 'fat-free',
        'low-fat', 'reduced-fat', 'unsalted', 'salted', 'softened', 'room temperature',
        'beaten', 'melted', 'shredded', 'cubed', 'peeled', 'seeded', 'halved', 'quartered',
        'crushed', 'crumbled', 'warm', 'cold', 'hot', 'boiling', 'cooked', 'uncooked',
        'frozen', 'thawed', 'dry', 'roasted', 'raw', 'rinsed', 'drained', 'divided', 'plus',
        'more', 'less', 'to taste', 'taste', 'for', 'serving', 'garnish', 'needed', 'see',
        'directions', 'instruction', 'and', 'or', 'with', 'without', 'as', 'desired', 'your',
        'favorite', 'optional', 'about', 'good quality', 'approximately', 'heaping', 'scant',
        'splash', 'handful', 'each', 'any amount', 'all-purpose', 'purpose', 'unbleached',
        'bleached', 'white', 'self-rising', 'self rising', 'self', 'rising', 'active', 'dry',
        'granulated', 'extra-virgin', 'confectioners', 'caster', 'powdered', 'packed', 'firmly',
        'lightly', 'firmly-packed', 'buttermilk', 'heavy', 'whipping', 'double', 'single',
        'strong', 'freshly', 'filtered', 'store-bought', 'store bought', 'homemade', 'prepared',
        'julienned', 'whole', 'broken', 'bottled', 'jarred', 'instant', 'quick', 'old-fashioned',
        'steel-cut', 'fine', 'medium', 'coarse', 'instant', 'regular', 'quick-cooking', 'soft',
        'hard', 'ripe', 'overripe', 'under-ripe', 'zest of', 'juice of', 'freshly squeezed',
        'at room temperature', 'slightly beaten', 'lightly beaten', 'hard-boiled', 'soft-boiled',
        'wedge', 'wedges', 'ring', 'rings', 'round', 'rounds', 'julienne', 'matchstick',
        'lengthwise', 'crosswise', 'thick', 'thin', 'thickly', 'thinly', 'bite-size',
        'bite sized', 'puree', 'purée', 'pureed', 'puréed', 'mashed', 'roughly chopped',
        'lightly packed', 'ounces', 'tablespoons', 'teaspoons', 'pounds', 'substitute', 'substitutes'
    ]
    for term in unwanted_terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        ingredient = re.sub(pattern, '', ingredient, flags=re.IGNORECASE)
    
    ingredient = re.sub(r'[,]', '', ingredient)
    ingredient = re.sub(r'\s+', ' ', ingredient).strip()
    
    doc = nlp(ingredient)
    lemmatized_tokens = []
    for token in doc:
        if not token.is_stop and token.is_alpha:
            if token.pos_ not in ['NOUN', 'PROPN']:
                lemma = token.lemma_
            else:
                lemma = token.text
            lemmatized_tokens.append(lemma)
    if lemmatized_tokens:
        ingredient = ' '.join(lemmatized_tokens)
    else:
        ingredient = ingredient
    
    for term in unwanted_terms:
        pattern = r'\b' + re.escape(term) + r'\b'
        ingredient = re.sub(pattern, '', ingredient, flags=re.IGNORECASE)
    
    ingredient = re.sub(r'\s+', ' ', ingredient).strip()
    
    if not ingredient or ingredient.lower() in units_list or ingredient.isdigit():
        return None
    
    return ingredient

async def make_page_queue(browser, page_queue, num_pages):
    for _ in range(num_pages):
        page = await browser.new_page()
        await page_queue.put(page)
    return page_queue
    
async def main():
    state = load_state()
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        pool = await create_pool()
        
        page_queue = asyncio.Queue()
        num_pages = 50
        page_queue = await make_page_queue(browser, page_queue, num_pages)
        letters = await get_page_letter(page_queue=page_queue)
        await get_recipe_links(browser=browser, letters=letters, pool=pool, state=state, page_queue=page_queue)
        
        while not page_queue.empty():
            page = await page_queue.get()
            await page.close()
            
        await pool.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())