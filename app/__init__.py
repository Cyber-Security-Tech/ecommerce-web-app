from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from datetime import timedelta

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # 🕒 Automatically log out after 30 minutes
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=30)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    # Redirect unauthorized users to login
    login_manager.login_view = 'main_bp.login'

    from . import routes
    app.register_blueprint(routes.main_bp)

    return app
