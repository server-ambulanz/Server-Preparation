# app/config.py
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env Datei
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv()

class Config:
    # Flask Konfiguration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change'
    FLASK_DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    # Datenbank Konfiguration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "database", "server-onboarding.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Auth0 Konfiguration
    AUTH0_CLIENT_ID = os.environ.get('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.environ.get('AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.environ.get('AUTH0_DOMAIN')
    AUTH0_BASE_URL = f'https://{AUTH0_DOMAIN}' if AUTH0_DOMAIN else None
    AUTH0_AUDIENCE = os.environ.get('AUTH0_AUDIENCE')
    
    # Server Konfiguration
    PORT = int(os.environ.get('PORT', 5001))