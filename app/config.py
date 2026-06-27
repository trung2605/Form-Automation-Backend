import os
from datetime import timedelta

class Config:
    # Basic
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key'
    
    # MongoDB
    MONGODB_SETTINGS = {
        'host': os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/auto_form_db'
    }
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-super-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
