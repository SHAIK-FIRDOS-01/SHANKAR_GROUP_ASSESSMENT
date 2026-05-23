import os
from dotenv import load_dotenv

# Load environmental variables from .env
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev_secret_key_change_me_in_production')
    
    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    if not SQLALCHEMY_DATABASE_URI or SQLALCHEMY_DATABASE_URI.strip() == "":
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    elif SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        # Support for older style Postgres URLs
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
