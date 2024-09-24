import time

from flask import Blueprint, jsonify, render_template

from ...database import refresh_db, run_db_population
from ...extensions import socketio

# Create a Blueprint
main = Blueprint("main", __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/refresh", methods=["POST"])
def refresh():
    start_time = time.time()
    # refresh_db()
    run_db_population()
    end_time = time.time()
    elapsed_time = end_time - start_time
    completed_message = f"Refresh executed in {elapsed_time:.2f} seconds"
    socketio.emit("log_message", {"message": completed_message})
    return jsonify({"message": completed_message})
