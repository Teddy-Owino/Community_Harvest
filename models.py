import pymysql
from config import Config


def get_db_connection():
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        db=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,  # Use the port from Config
        cursorclass=pymysql.cursors.DictCursor
    )


def create_user(username, email):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO users (username, email) VALUES (%s, %s)", (username, email))
    connection.commit()
    cursor.close()
    connection.close()

def get_all_users():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    cursor.close()
    connection.close()
    return users

def create_event(title, date, location, description):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO events (title, date, location, description) VALUES (%s, %s, %s, %s)", (title, date, location, description))
    connection.commit()
    cursor.close()
    connection.close()

def get_all_events():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM events")
    events = cursor.fetchall()
    cursor.close()
    connection.close()
    connection.close()
    return events

def create_recipe(title, ingredients, instructions):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO recipes (title, ingredients, instructions) VALUES (%s, %s, %s)", (title, ingredients, instructions))
    connection.commit()
    cursor.close()
    connection.close()

def get_all_recipes():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM recipes")
    recipes = cursor.fetchall()
    cursor.close()
    connection.close()
    return recipes

def create_volunteer(name, email):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO volunteers (name, email) VALUES (%s, %s)", (name, email))
    connection.commit()
    cursor.close()
    connection.close()

def get_all_volunteers():
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM volunteers")
    volunteers = cursor.fetchall()
    cursor.close()
    connection.close()
    return volunteers
