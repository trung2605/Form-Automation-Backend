from flask import Flask
from flask_cors import CORS
import mongoengine
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from app.config import Config

jwt = JWTManager()
bcrypt = Bcrypt()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['JSON_SORT_KEYS'] = False

    CORS(app, origins=["https://form-automation-frontend.vercel.app", "http://localhost:3000"])

    # Connect to MongoDB using the URI from Config
    mongoengine.connect(host=app.config['MONGODB_SETTINGS']['host'])

    # Initialize Extensions
    jwt.init_app(app)
    bcrypt.init_app(app)

    # Register Blueprints
    from app.controllers.auth import auth_bp
    from app.controllers.payment import payment_bp
    from app.controllers.forms import forms_bp
    from app.controllers.admin import admin_bp
    from app.controllers.tool import tool_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(payment_bp, url_prefix='/api/payment')
    app.register_blueprint(forms_bp, url_prefix='/api/forms')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(tool_bp, url_prefix='/api/tools')

    return app
