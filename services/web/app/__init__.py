import os
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["DATABASE_URL"] = os.environ.get("DATABASE_URL")

    from app.routes import main
    app.register_blueprint(main)

    return app
