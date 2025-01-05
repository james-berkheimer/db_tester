# src/db_tester/config.py

import os


class DBConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///db_tester.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ServerConfig:
    HOST = os.getenv("FLASK_RUN_HOST", "127.0.0.1")
    PORT = int(os.getenv("FLASK_RUN_PORT", 5090))
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"


class PlexConfig:
    CRED_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tests/.plex_cred/credentials.json"
    )
