"""
database.py

Sets up the SQLAlchemy database engine and session factory.
All other modules import from here to get database access.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the database URL from environment — defaults to local SQLite if not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mediaflow.db")

# Create the engine — this is the core connection to the database
# check_same_thread is False because FastAPI can handle multiple threads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a factory — calling it gives you a database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class all our models will inherit from
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI.
    Yields a database session and ensures it closes after each request,
    even if an error occurs — this prevents connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()