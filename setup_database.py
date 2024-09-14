import pymysql

def connect():
    timeout = 10
    connection = pymysql.connect(
        charset="utf8mb4",
        connect_timeout=timeout,
        cursorclass=pymysql.cursors.DictCursor,
        db="food-suggester",
        host="mysql-food-suggester-food-suggester.h.aivencloud.com",
        password="AVNS_fL1GBLVBNF4rHJjxi8v",
        read_timeout=timeout,
        port=16180,
        user="avnadmin",
        write_timeout=timeout,
    )
    return connection

def create_tables(connection):
    cursor = connection.cursor()
    cursor.execute(
    """
    CREATE TABLE IF NOT EXISTS Recipes (
        recipe_id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_name VARCHAR(255) NOT NULL,
        number_of_ingredients INT NOT NULL,
        number_of_steps INT NOT NULL,
        number_of_servings VARCHAR(10) NOT NULL,
        preparation_time INT NOT NULL,
        raw_ingredients TEXT NOT NULL,
        number_of_ratings INT NOT NULL,
        recipe_link VARCHAR(255) NOT NULL
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Instructions (
        instruction_id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_id INT NOT NULL,
        step_number INT NOT NULL,
        instruction TEXT NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id) ON DELETE CASCADE
    )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS IngredientsQuantity (
        iq_id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_id INT NOT NULL,
        ingredient_name VARCHAR(255) NOT NULL,
        FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id) ON DELETE CASCADE
    )
    """)
  
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CleanIngredients (
        clean_ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
        iq_id INT NOT NULL,
        clean_ingredient VARCHAR(255) NOT NULL,
        FOREIGN KEY (iq_id) REFERENCES IngredientsQuantity(iq_id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Categories (
        category_id INT AUTO_INCREMENT PRIMARY KEY,
        category VARCHAR(255) NOT NULL
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RecipeCategory (
        recipe_id INT NOT NULL,
        category_id INT NOT NULL,
        PRIMARY KEY (recipe_id, category_id),
        FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
    )
    """)
    
def insert_recipe(connection, recipe_name, number_of_ingredients, number_of_steps, number_of_servings, 
                    preparation_time, raw_ingredients, number_of_ratings, recipe_link):
    cursor = connection.cursor()
  
    check_query = """
    SELECT COUNT(*) FROM Recipes WHERE recipe_name = %s AND recipe_link = %s
    """
    cursor.execute(check_query, (recipe_name, recipe_link))
    result = cursor.fetchone()
    
    if result['COUNT(*)'] == 0:
        insert_query = """
        INSERT INTO Recipes (recipe_name, number_of_ingredients, number_of_steps, number_of_servings, 
                        preparation_time, raw_ingredients, number_of_ratings, recipe_link)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (recipe_name, number_of_ingredients, number_of_steps, number_of_servings, 
                        preparation_time, raw_ingredients, number_of_ratings, recipe_link))
        connection.commit()
         
def main():
    connection = None
    try:
        connection = connect()
        create_tables(connection)
    except pymysql.MySQLError as err:
        print(f"Error: {err}")
    finally:
        if connection:
            connection.close()
  
if __name__ == "__main__":
    main()