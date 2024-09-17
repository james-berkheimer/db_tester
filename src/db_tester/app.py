import time

from flask import Flask

from .config import DBConfig
from .extensions import db
from .populate_db import populate_db


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        start_time = time.time()
        populate_db()
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"populate_db function executed in {elapsed_time:.2f} seconds")


def create_app():
    # create the app
    app = Flask(__name__)
    # configure the SQLite database, relative to the app instance folder
    app.config.from_object(DBConfig)

    # initialize the app with the extension
    # db.init_app(app)

    # Initialize database
    init_db(app)

    return app


app = create_app()
