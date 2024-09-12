from playwright.sync_api import sync_playwright
import pandas as pd

def get_page_letter(browser):
    link = "https://www.food.com/browse/allrecipes/?page=1&letter=123"

    page = browser.new_page()
    page.goto(link)
    
    magic_columns = page.locator('//div[@class="letter-filters magic-buttons"]/ul/li[contains(@class, "magic-columns-3")]')
    magic_columns_count = magic_columns.count()
    letters = []
    for i in range(magic_columns_count):
        li_element = magic_columns.nth(i)
        ul_element = li_element.locator('ul')
        li_count = ul_element.locator('li').count()
        for j in range(li_count):
            inner_li_element = ul_element.locator('li').nth(j)
            li_class = inner_li_element.get_attribute('class')
            if li_class == 'selected':
                letter = inner_li_element.inner_html()
            else:
                letter = inner_li_element.locator('a').inner_text()
            letters.append(letter)
    page.close()
    return letters

def get_recipe_links(browser, letters):
    all_recipe_links = []

    for letter in letters:
        page_url = f"https://www.food.com/browse/allrecipes/?page=1&letter={letter}"
        page = browser.new_page()
        page.goto(page_url)
        last_page = int(page.locator('//li[@class="page  page-last  js-paging-after"]/a').inner_text())
        page.close()
        for page in range(1, last_page + 1):
            base_url = f"https://www.food.com/browse/allrecipes/?page={page}&letter={letter}"
            link = base_url.format(page=page, letter=letter)
            page = browser.new_page()
            page.goto(link)
            
            recipe_section = page.locator('//div[@class="content-columns"]')
            tabs_count = recipe_section.locator('div').count()
            for tab in range(tabs_count):
                ul_section = recipe_section.locator('div').nth(tab).locator('ul')
                li_count = ul_section.locator('li').count()
                recipe_links = []
                for li in range(li_count):
                    links = ul_section.locator('li').nth(li).locator('a')
                    for recipe_link in links.element_handles():
                        r_link = recipe_link.get_attribute('href')
                        recipe_links.append(r_link)
                # save_to_csv(recipe_links, "recipes.csv")
                all_recipe_links.append(recipe_links)
            page.close()
            # print(all_recipe_links)
    # print(all_recipe_links)
    return all_recipe_links

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, mode='a', header=not pd.io.common.file_exists(filename), index=False)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        letters = get_page_letter(browser=browser)
        all_recipe_links = get_recipe_links(browser=browser, letters=letters)
        browser.close()
        
if __name__ == "__main__":
    main()