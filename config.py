import os
from dotenv import load_dotenv

# Load environment variables from .env file (optional for local development)
load_dotenv()

class Config:
    # MySQL database connection info from environment variables
    MYSQL_HOST = os.getenv('DB_HOST')  # Default to 'localhost' if not set
    MYSQL_USER = os.getenv('DB_USER')  # Default to 'root' if not set
    MYSQL_DB = os.getenv('DB_NAME')  # Default to your local database
    MYSQL_PASSWORD = os.getenv('DB_PASSWORD')  # Default to 3306 (MySQL port)
    
    # Flask secret key (for session management and CSRF protection)
    import os
from dotenv import load_dotenv

# Load environment variables from .env file (optional for local development)
load_dotenv()

class Config:
    # MySQL database connection info from environment variables
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')  # Default to 'localhost' if not set
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')  # Default to 'root' if not set
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')  # Default to empty if not set
    MYSQL_DB = os.getenv('MYSQL_DB', 'community_harvest_db')  # Default to your local database
    MYSQL_PORT = os.getenv('MYSQL_PORT', 3306)  # Default to 3306 (MySQL port)
    
    # Flask secret key (for session management and CSRF protection)
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key-for-local-development')

