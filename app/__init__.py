from flask import Flask
from flask_migrate import Migrate
from .database import db

def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(f'config.{config_name.capitalize()}Config')

    db.init_app(app)
    Migrate(app, db)

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app