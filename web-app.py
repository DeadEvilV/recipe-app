from flask import Flask, render_template, request, jsonify, abort
from sqlalchemy import create_engine, text
import random

app = Flask(__name__)

DATABASE_URL = 'mysql+mysqlconnector://avnadmin:AVNS_fL1GBLVBNF4rHJjxi8v@mysql-food-suggester-food-suggester.h.aivencloud.com:16180/food-suggester'
engine = create_engine(DATABASE_URL)

@app.route('/')
def index():
    with engine.connect() as connection:
        random_recipes = connection.execute(text(
            "SELECT recipe_name, recipe_link FROM Recipes ORDER BY RAND() LIMIT 20"
        )).fetchall()
    return render_template('index.html', random_recipes=random_recipes)

@app.route('/search', methods=['GET'])
def search_recipes():
    query = request.args.get('query')
    if query:
        with engine.connect() as connection:
            results = connection.execute(text(
                "SELECT recipe_name, recipe_link FROM Recipes WHERE recipe_name LIKE :query"
            ), {'query': f'%{query}%'}).fetchall()
        return render_template('search_results.html', results=results, query=query)
    return render_template('search_results.html', results=[], query='')

@app.route('/categories')
def categories():
    with engine.connect() as connection:
        categories = connection.execute(text(
            "SELECT category_id, category FROM Categories ORDER BY category ASC"
        )).fetchall()
    return render_template('categories.html', categories=categories)

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

@app.route('/random_recipes', methods=['GET'])
def random_recipes():
    with engine.connect() as connection:
        random_recipes = connection.execute(text(
            "SELECT recipe_name, recipe_link FROM Recipes ORDER BY RAND() LIMIT 10"
        )).fetchall()
    return jsonify([dict(recipe) for recipe in random_recipes])

if __name__ == '__main__':
    app.run(debug=True)
