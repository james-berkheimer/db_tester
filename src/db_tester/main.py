import os
import sys


def main():
    print("Hello, world!")
    os.environ["FLASK_APP"] = "db_tester.app"
    os.environ["PLEX_CRED"] = "/home/james/code/db_tester/tests/.plex_cred"

    os.environ["FLASK_RUN_HOST"] = "127.0.0.1"
    os.environ["FLASK_RUN_PORT"] = str(5090)
    os.environ["FLASK_DEBUG"] = "0"
    os.system("flask run")

    sys.argv = ["flask", "run"]
    os.system(" ".join(sys.argv))
