import aiomysql
import asyncio

async def create_pool():
    pool = await aiomysql.create_pool(
        host="mysql-food-suggester-food-suggester.h.aivencloud.com",
        port=16180,
        user="avnadmin",
        password="AVNS_fL1GBLVBNF4rHJjxi8v",
        db="food-suggester",
        charset="utf8mb4",
        autocommit=True,
        minsize=5,
        maxsize=30,
        cursorclass=aiomysql.DictCursor
    )
    return pool

async def create_tables(pool):
    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("""
            CREATE TABLE IF NOT EXISTS Recipes (
                recipe_id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_name VARCHAR(255) NOT NULL,
                number_of_ingredients INT NOT NULL,
                number_of_steps INT NOT NULL,
                number_of_servings VARCHAR(10) NOT NULL,
                preparation_time INT NOT NULL,
                ingredients_list TEXT NOT NULL,
                number_of_ratings INT NOT NULL,
                recipe_link VARCHAR(255) NOT NULL
            )
            """)

            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS Instructions (
                instruction_id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_id INT NOT NULL,
                step_number INT NOT NULL,
                instruction TEXT NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id) ON DELETE CASCADE
            )
            """)

            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS CleanIngredients (
                clean_ingredient_id INT AUTO_INCREMENT PRIMARY KEY,
                recipe_id INT NOT NULL,
                clean_ingredient VARCHAR(255) NOT NULL,
                FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id) ON DELETE CASCADE
            )
            """)

            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS Categories (
                category_id INT AUTO_INCREMENT PRIMARY KEY,
                category VARCHAR(255) NOT NULL
            )
            """)

            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS RecipeCategory (
                recipe_id INT NOT NULL,
                category_id INT NOT NULL,
                PRIMARY KEY (recipe_id, category_id),
                FOREIGN KEY (recipe_id) REFERENCES Recipes(recipe_id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES Categories(category_id) ON DELETE CASCADE
            )
            """)
    
async def insert_recipe(pool, recipe_data, direction_dict, clean_ingredients, category):
    async with pool.acquire() as connection:
        async with connection.cursor() as cursor:
            try:
                await cursor.execute("START TRANSACTION;")
                check_query = """
                SELECT COUNT(*) as count FROM Recipes WHERE recipe_name = %s AND recipe_link = %s
                """
                await cursor.execute(check_query, (recipe_data['recipe_name'], recipe_data['recipe_link']))
                result = await cursor.fetchone()
                if result['count'] == 0:
                    insert_query = """
                    INSERT INTO Recipes (recipe_name, number_of_ingredients, number_of_steps, number_of_servings, 
                                        preparation_time, ingredients_list, number_of_ratings, recipe_link)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    await cursor.execute(insert_query, (
                        recipe_data['recipe_name'],
                        recipe_data['number_of_ingredients'],
                        recipe_data['number_of_steps'],
                        recipe_data['number_of_servings'],
                        recipe_data['preparation_time'],
                        str(recipe_data['ingredients_list']),
                        recipe_data['number_of_ratings'],
                        recipe_data['recipe_link']
                    ))
                    
                    await cursor.execute("SELECT LAST_INSERT_ID();")
                    recipe_id = (await cursor.fetchone())['LAST_INSERT_ID()']
                    for step, instruction in direction_dict.items():
                        insert_instruction_query = """
                        INSERT INTO Instructions (recipe_id, step_number, instruction)
                        VALUES (%s, %s, %s)
                        """
                        await cursor.execute(insert_instruction_query, (
                            recipe_id,
                            int(step),
                            instruction.strip()
                        ))
                    
                    for clean_ingredient in clean_ingredients:
                        if clean_ingredient:
                            insert_clean_ingredient_query = """
                            INSERT INTO CleanIngredients (recipe_id, clean_ingredient)
                            VALUES (%s, %s)
                            """
                            await cursor.execute(insert_clean_ingredient_query, (
                                recipe_id,
                                clean_ingredient.strip()
                            ))
                            
                    if category:
                        check_category_query = """SELECT category_id from Categories WHERE category = %s;"""
                        await cursor.execute(check_category_query, (category,))
                        category_result = await cursor.fetchone()
                        
                        if category_result:
                            category_id = category_result['category_id']
                        else:
                            insert_category_query = """
                            INSERT INTO Categories (category)
                            VALUES (%s);
                            """
                            await cursor.execute(insert_category_query, (category.strip(),))
                            await cursor.execute("SELECT LAST_INSERT_ID();")
                            category_id = (await cursor.fetchone())['LAST_INSERT_ID()']

                        insert_recipe_category_query = """
                        INSERT INTO RecipeCategory (recipe_id, category_id)
                        VALUES (%s, %s)
                        """
                        await cursor.execute(insert_recipe_category_query, (
                            recipe_id,
                            category_id
                        ))
                await cursor.execute("COMMIT;")
            except Exception as e:
                await cursor.execute("ROLLBACK;")
                print(f"Error: {e}")
         
async def init():
    pool = await create_pool()
    try:
        await create_tables(pool)
    finally:
        pool.close()
        await pool.wait_closed()
  
if __name__ == "__main__":
    asyncio.run(init())