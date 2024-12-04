from flask import Flask, render_template, request, redirect, url_for
from sqlalchemy import create_engine, text
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
import ast
import pandas as pd

app = Flask(__name__)
app.secret_key = 'DUH342I54hF2IUdHaIHFGHE'

DATABASE_URI = 'mysql+mysqlconnector://(password)@localhost:3306/food-suggester'
engine = create_engine(DATABASE_URI)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

def create_tables():
    create_users_table_query = """
        CREATE TABLE IF NOT EXISTS Users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(100) NOT NULL
        )
    """
    
    create_user_preferences_ingredients_table_query = """
        CREATE TABLE IF NOT EXISTS UserPreferencesIngredients (
        user_preference_ingredients_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        ingredient_name VARCHAR(100),
        FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """
    
    create_user_preferences_categories_table_query = """
        CREATE TABLE IF NOT EXISTS UserPreferencesCategories (
        user_preference_categories_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT,
        category VARCHAR(100),
        FOREIGN KEY (user_id) REFERENCES Users(id)
        )
    """
    
    with engine.connect() as connection:
        connection.execute(text(create_users_table_query))
        connection.execute(text(create_user_preferences_ingredients_table_query))
        connection.execute(text(create_user_preferences_categories_table_query))

@login_manager.user_loader
def load_user(user_id):
    with engine.connect() as connection:
        user = connection.execute(text("SELECT id, username, password FROM Users WHERE id = :id"),
                                  {'id': user_id}).fetchone()
        if user:
            return User(id=user.id, username=user.username, password=user.password)
        return None
    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with engine.connect() as connection:
            user = connection.execute(text("SELECT id, username, password FROM Users WHERE username = :username AND password = :password"), 
                                      {'username': username, 'password': password}).fetchone()
            if user:
                login_user(User(id=user.id, username=user.username, password=user.password))
                return redirect(url_for('index'))
        return 'Invalid credentials'
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        selected_ingredients = request.form.getlist('ingredients')
        selected_categories = request.form.getlist('categories')
        
        with engine.begin() as connection:
            connection.execute(text("""
                INSERT INTO Users (username, password) 
                VALUES (:username, :password)
            """), {'username': username, 'password': password})
            
            user_id = connection.execute(text("SELECT LAST_INSERT_ID()")).fetchone()[0]
            
            for ingredient in selected_ingredients:
                connection.execute(text("""
                    INSERT INTO UserPreferencesIngredients (user_id, ingredient_name)
                    VALUES (:user_id, :ingredient_name)
                """), {'user_id': user_id, 'ingredient_name': ingredient})

            for category in selected_categories:
                connection.execute(text("""
                    INSERT INTO UserPreferencesCategories (user_id, category)
                    VALUES (:user_id, category)
                """), {'user_id': user_id, 'category': category})
        return redirect(url_for('login'))
    else:
        with engine.connect() as connection:
            top_ingredients = connection.execute(text("""
                SELECT clean_ingredient
                FROM CleanIngredients
                GROUP BY clean_ingredient
                ORDER BY COUNT(*) DESC
                LIMIT 100
            """)).fetchall()
            top_ingredients = [row[0] for row in top_ingredients]
            
            categories = connection.execute(text("""
                SELECT category
                FROM Categories
                """)).fetchall()
            categories = [row[0] for row in categories]

        return render_template('register.html', ingredients=top_ingredients, categories=categories)

@app.route('/')
@login_required
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
@login_required
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
@login_required
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
@login_required
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
            
def get_user_profile(user_id):
    with engine.connect as connection:
        preferred_ingredients = connection.execute(text("""
            SELECT ingredient_name
            FROM UserPreferencesIngredients
            WHERE user_id = :user_id
        """), {'user_id': user_id}).fetchall()
        
        preferred_categories = connection.execute(text("""
            SELECT category
            FROM UserPreferencesCategories
            WHERE user_id = :user_id
        """), {'user_id': user_id}).fetchall()

        preferred_ingredients = [row[0] for row in preferred_ingredients]
        preferred_categories = [row[0] for row in preferred_categories]
        
        user_profile = {
            'preferred_ingredients': preferred_ingredients,
            'preferred_categories': preferred_categories
        }
        
        return user_profile
    
if __name__ == '__main__':
    create_tables()

    app.run(debug=True)