import logging
import os
import time

import click

from .app import app
from .database.extensions import db
from .utils import create_logger


@click.command()
@click.option("-d", "--debugger", is_flag=True, help="Runs the server with debugger.")
@click.option("-h", "--host", default="127.0.0.1", help="Specify the host IP address.")
@click.option("-p", "--port", default=5090, help="Specify the port to run on.")
@click.option("-v", "--verbose", count=True, help="Increase verbosity level")
def main(debugger, host, port, verbose):
    if verbose == 0:
        log_level = logging.WARNING
    elif verbose == 1:
        log_level = logging.INFO
    elif verbose >= 2:
        log_level = logging.DEBUG

    logger = create_logger(level=log_level)
    app.logger = logger

    init_db()

    os.environ["FLASK_APP"] = "db_tester.app"
    os.environ["PLEX_CRED"] = "/home/james/code/db_tester/tests/.plex_cred"

    os.environ["FLASK_RUN_HOST"] = host
    os.environ["FLASK_RUN_PORT"] = str(port)

    if debugger:
        os.environ["FLASK_DEBUG"] = "1"

    app.run(host=host, port=port, debug=debugger)


def init_db():
    from .database import DatabasePopulator

    populator = DatabasePopulator()
    db.init_app(app)
    with app.app_context():
        db.create_all()
        start_time = time.time()
        populator.run_db_population()
        end_time = time.time()
        elapsed_time = end_time - start_time
        app.logger.info(f"populate_db function executed in {elapsed_time:.2f} seconds")


if __name__ == "__main__":
    main()
