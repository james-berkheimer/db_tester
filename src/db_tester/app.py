import os
import time

from flask import Flask

from .apps.refresh.routes import main
from .config import DBConfig
from .database import run_db_population
from .extensions import db, socketio


def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        start_time = time.time()
        run_db_population()
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"populate_db function executed in {elapsed_time:.2f} seconds")


def create_app():
    app = Flask(__name__)

    # configure the SQLite database, relative to the app instance folder
    app.config.from_object(DBConfig)

    # if os.getenv("IGNORE_DB_CREATION") == "1":
    init_db(app)

    # Initialize SocketIO
    socketio.init_app(app)

    # Register the Blueprint
    app.register_blueprint(main)

    return app


app = create_app()
if __name__ == "__main__":
    socketio.run(app)
