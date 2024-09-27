from flask import Flask, render_template, request
from sqlalchemy import create_engine, text
import ast

app = Flask(__name__)

DATABASE_URI = 'mysql+mysqlconnector://avnadmin:AVNS_fL1GBLVBNF4rHJjxi8v@mysql-food-suggester-food-suggester.h.aivencloud.com:16180/food-suggester'
engine = create_engine(DATABASE_URI)

@app.route('/')
def index():
    with engine.connect() as connection:
        random_recipes = connection.execute(text(
            "SELECT recipe_name, recipe_link FROM Recipes ORDER BY RAND() LIMIT 20"
        )).fetchall()
        categories = connection.execute(text(
            "SELECT category_id, category FROM Categories ORDER BY category ASC"
        )).fetchall()
        recipe_links = []
        for recipe in random_recipes:
            name, url = recipe
            replace_string = 'https://www.food.com/recipe/'
            recipe_link = url.replace(replace_string, '')
            recipe_links.append((name, recipe_link))
    return render_template('index.html', recipe_links=recipe_links, categories=categories)

@app.route('/category/<int:category_id>')
def category_recipes(category_id):
    with engine.connect() as connection:
        recipes = connection.execute(text(
            "SELECT recipe_name, recipe_link FROM Recipes r "
            "JOIN RecipeCategory rc ON r.recipe_id = rc.recipe_id "
            "WHERE rc.category_id = :category_id LIMIT 20"
        ), {'category_id': category_id}).fetchall()
        
        category_name_query = connection.execute(text(
            "SELECT category FROM Categories WHERE category_id = :category_id"
        ), {'category_id': category_id}).fetchone()
        category_name = category_name_query[0]
    return render_template('category_recipes.html', recipes=recipes, category_name=category_name)

@app.route('/recipe/<path:recipe_link>')
def go_to_recipe(recipe_link):
    with engine.connect() as connection:
        base_url = 'https://www.food.com/recipe/'
        full_recipe_link = base_url + recipe_link
        get_recipe_data = connection.execute(text(
            "SELECT recipe_id, recipe_name, number_of_ingredients, number_of_servings, preparation_time, ingredients_list FROM Recipes WHERE recipe_link = :full_recipe_link"
        ), {'full_recipe_link': full_recipe_link}).fetchone()
        if get_recipe_data:
            recipe_id = get_recipe_data[0]
            get_category = connection.execute(text(
            "SELECT c.category_id, c.category FROM RecipeCategory rc JOIN Categories c ON rc.category_id = c.category_id WHERE rc.recipe_id = :recipe_id"
        ), {'recipe_id': recipe_id}).fetchone()
            get_recipe_instructions = connection.execute(text(
                "SELECT step_number, instruction FROM Instructions WHERE recipe_id = :recipe_id"
            ), {'recipe_id': recipe_id}).fetchall()
            ingredients_list = ast.literal_eval(get_recipe_data.ingredients_list)
    return render_template('recipe_page.html', get_recipe_data=get_recipe_data, ingredients_list=ingredients_list, get_category=get_category, get_recipe_instructions=get_recipe_instructions)

@app.route('/search', methods=['GET'])
def search():
    search_query = str(request.args.get('search_query')).lower()
    if search_query:
        with engine.connect() as connection:
            search_results = connection.execute(text(
                "SELECT LOWER(recipe_name), recipe_link FROM Recipes WHERE recipe_name LIKE :search_query"
            ), {'search_query': f'%{search_query}%'}).fetchall()
            
            recipe_links = []
            for recipe in search_results:
                name, url = recipe
                replace_string = 'https://www.food.com/recipe/'
                recipe_link = url.replace(replace_string, '')
                recipe_links.append((name, recipe_link))
        return render_template('search_results.html', search_query=search_query, search_results=recipe_links)
    return render_template('search_results.html', search_query=search_query, search_results=[])
            
    
if __name__ == '__main__':
    app.run(debug=True)
