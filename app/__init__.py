from flask import Flask, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
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

    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(minutes=30)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'main_bp.login'

    from .models import CartItem
    @app.before_request
    def load_cart_count():
        if current_user.is_authenticated:
            g.cart_count = sum(item.quantity for item in CartItem.query.filter_by(user_id=current_user.id).all())
        else:
            g.cart_count = 0

    from . import routes
    app.register_blueprint(routes.main_bp)

    return app
