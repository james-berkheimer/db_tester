# import time

from flask import Flask

from .apps.refresh.routes import main
from .config import DBConfig, ServerConfig
from .extensions import socketio


def create_app():
    app = Flask(__name__)
    app.config.from_object(DBConfig)
    socketio.init_app(app)
    app.register_blueprint(main)
    return app


app = create_app()
if __name__ == "__main__":
    socketio.run(app, host=ServerConfig.HOST, port=ServerConfig.PORT, debug=ServerConfig.DEBUG)
