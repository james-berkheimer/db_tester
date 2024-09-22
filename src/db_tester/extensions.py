from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
socketio = SocketIO()

# Initialize session as None
# session = None


db_path = "sqlite:///src/instance/db_tester.db"
# Create an engine and connect to the database
engine = create_engine(db_path)
metadata = MetaData()
metadata.reflect(bind=engine)
# Create a session
Session = sessionmaker(bind=engine)
session = Session()


# def init_session(db_path):
#     print(f"Initializing session with database path: {db_path}")
#     global session
#     # Extract the actual file path from the URI
#     db_file_path = db_path.replace("sqlite:///", "")

#     # Check if the database file exists before creating the engine
#     if os.path.exists(db_file_path):
#         # Create an engine and connect to the database
#         engine = create_engine(db_path)
#         metadata = MetaData()
#         metadata.reflect(bind=engine)
#         # Create a session
#         Session = sessionmaker(bind=engine)
#         session = Session()
#     else:
#         print(f"Database file {db_file_path} does not exist. Skipping engine creation.")
