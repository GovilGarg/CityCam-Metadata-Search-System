import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv


# Load the secrets from the password.env file and push it into the system environment 
env_path = os.path.join(os.path.dirname(__file__), "password.env")
load_dotenv(env_path)

def get_connection():        
    try:
        my_db = mysql.connector.connect(

            host=os.getenv("DB_HOST", "127.0.0.1"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASS"),
            database=os.getenv("DB_NAME"),
            port = 3306
        )
        return my_db
    except Error as e:
        print(f"ERROR: {e}")
        return None