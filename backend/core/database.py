import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from dotenv import load_dotenv

# Load the passwords from your .env file
load_dotenv(dotenv_path="../.env") # Pointing to the .env in the root folder

DB_USER = os.getenv("POSTGRES_USER", "admin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "clipmind_users")

# This is the exact URL connecting to your Docker container
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/{DB_NAME}"

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

from pymongo import MongoClient

# MongoDB Client connection pointing to the running Docker container
mongo_client = MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["clipmind_db"]