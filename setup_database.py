import mysql.connector

def connect_to_mysql():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Gorkemozan246!"
    )
    cursor = conn.cursor()
    return conn, cursor

def create_database(conn, cursor):
    cursor.execute("CREATE DATABASE IF NOT EXISTS food_suggest_db")
    conn.commit()
    cursor.close()
    conn.close()

def connect_to_database():
    conn = mysql.connector.connect(
        host = "localhost",
        user = "root",
        password = "Gorkemozan246!",
        database = "food_suggest_db"
    )

    cursor = conn.cursor()
    return conn, cursor

def create_tables(conn, cursor):
    create_all_tables = """
    CREATE TABLE IF NOT EXISTS recipes (
        recipe_id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_name VARCHAR(255) NOT NULL,
        number_of_ingredients INT NOT NULL,
        number_of_steps INT NOT NULL,
        number_of_servings INT NOT NULL,
        preparation_time INT NOT NULL,
        source_url VARCHAR(255) NOT NULL
    );
  
    CREATE TABLE IF NOT EXISTS Instructions (
        instruction_id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_id INT NOT NULL,
        step_number INT NOT NULL,
        instruction TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
    );
    
    CREATE TABLE IF NOT EXISTS IngredientsQuantity (
        iq_id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_id INT NOT NULL,
        ingredient_name VARCHAR(255) NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS CleanIngredients (
        clean_ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
        iq_id INT NOT NULL,
        clean_ingredient VARCHAR(255) NOT NULL,
        FOREIGN KEY (iq_id) REFERENCES IngredientsQuantity(iq_id) ON DELETE CASCADE
    );
    
    CREATE TABLE IF NOT EXISTS Categories (
        category_id INT AUTO_INCREMENT PRIMARY KEY,
        category VARCHAR(255) NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS RecipeCategory (
    recipe_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (recipe_id, category_id),
    FOREIGN KEY (recipe_id) REFERENCES recipes(recipe_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
    );
    """
    for command in create_all_tables.split(';'):
        if command.strip():
            cursor.execute(command)
    conn.commit()
    cursor.close()
    conn.close()
    
def main():
    conn, cursor = connect_to_mysql()
    create_database(conn, cursor)
    
    conn, cursor = connect_to_database()
    create_tables(conn, cursor)
  
if __name__ == "__main__":
    main()