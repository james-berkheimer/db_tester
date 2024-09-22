import os
import sys

import click

from .utils.logging import LOGGER


@click.command()
@click.option("-d", "--debugger", is_flag=True, help="Runs the server with debugger.")
@click.option("-h", "--host", default="127.0.0.1", help="Specify the host IP address.")
@click.option("-p", "--port", default=5090, help="Specify the port to run on.")
# @click.option("-db", "--database", is_flag=True, help="Populate DB with test data.")
def main(debugger, host, port):
    LOGGER.info("Starting Database Tester")
    os.environ["FLASK_APP"] = "db_tester.app"
    os.environ["PLEX_CRED"] = "/home/james/code/db_tester/tests/.plex_cred"

    os.environ["FLASK_RUN_HOST"] = host
    os.environ["FLASK_RUN_PORT"] = str(port)

    if debugger:
        os.environ["FLASK_DEBUG"] = "1"

    # if database:
    #     os.environ["IGNORE_DB_CREATION"] = "1"
    # else:
    #     os.environ["IGNORE_DB_CREATION"] = "0"

    os.system("flask run")

    sys.argv = ["flask", "run"]
    os.system(" ".join(sys.argv))
