from playwright.sync_api import sync_playwright

def get_recipe_links(browser):
    recipe_links = []
    link = "https://www.allrecipes.com/recipe/278090/air-fryer-buffalo-cauliflower/"
    page = browser.new_page()
    page.goto(link)
    title = page.locator("h1").inner_text()
    ingredients = page.locator("span.recipe-ingred_txt.added").inner_text()
    print(title)
    print(ingredients)
    return recipe_links

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        recipe_links = get_recipe_links(browser)
        browser.close()