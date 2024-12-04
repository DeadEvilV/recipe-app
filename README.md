# Recipe App

This project represents an effort to experiment with web development while engaging with the challenges of processing unstructured data. My primary aim was to explore the integration of backend, database, and web scraping technologies in a cohesive application.

## What I Did

- **Backend with Flask**:  
  Flask served as the backbone of the application, handling routing and enabling dynamic content delivery. It provided the framework for creating a functional and responsive web application.

- **Database Management with SQL**:  
  I used a relational database to store and organize recipe data efficiently.

- **Web Scraping with Playwright**:  
  To get recipes, I used Playwright to scrape recipes from food.com. This process involved managing and processing unstructured web data into a structured format usable by the application.

- **CSS and Frontend Styling**:  
  The CSS used in this project was not written by me. As styling was not the primary focus of this project, I utilized pre-existing templates and tools. My efforts were concentrated on the backend functionality and data processing.

- **Limitations**:  
  While the app allows users to browse and search recipes, I have not yet implemented a recommendation system.

## Motivation

The project was an opportunity to:
- Work with unstructured data and transform it into something useful.
- Develop skills in integrating web scraping tools with backend services and databases.

This app is an ongoing learning experience, with room for improvement and expansion.

## How to Test It Locally

1. **Install Dependencies**:  
   Ensure you have Python installed. Then, install the required dependencies using `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

## How to Test It Locally

2. **Create the Database**:  
   Use the `food-suggester.sql` file provided in this repository to set up the database:
   - Open your MySQL client (Workbench, CLI, etc.).
   - Create the database:
     ```sql
     CREATE DATABASE food-suggester;
     ```
   - Import the SQL file:
     ```bash
     mysql -u root -p food-suggester < path/to/food-suggester.sql
     ```

3. **Set the Correct Password**:  
   Open `web-app.py` and `setup_database.py` files and update the database password to match your local MySQL configuration.
