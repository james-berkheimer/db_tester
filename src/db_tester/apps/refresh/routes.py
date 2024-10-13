import time

from flask import Blueprint, current_app, jsonify, render_template

from ...database import DatabasePopulator
from ...database.extensions import socketio

populator = DatabasePopulator()
main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/refresh", methods=["POST"])
def refresh():
    current_app.logger.info("Refreshing database")
    start_time = time.time()
    populator.run_db_population()
    end_time = time.time()
    elapsed_time = end_time - start_time
    completed_message = f"Refresh executed in {elapsed_time:.2f} seconds"
    socketio.emit("log_message", {"message": completed_message})
    return jsonify({"message": completed_message})
