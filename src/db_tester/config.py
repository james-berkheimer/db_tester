import os


class DBConfig:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///db_tester.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
