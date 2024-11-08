from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .auth import setup_auth

db = SQLAlchemy()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('app.config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    
    setup_auth(app)
    
    from .routes import main, auth
    app.register_blueprint(main)
    app.register_blueprint(auth)
    
    return app