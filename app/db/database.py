# /ata-backend/app/db/database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Get the database URL from the environment variable we set on Railway.
# The second argument is a default value for local development.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# Create the SQLAlchemy engine.
# The 'check_same_thread' argument is only needed for SQLite.
engine_args = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_args)

# Create a SessionLocal class. Each instance of this class will be a database session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a Base class. Our database model classes will inherit from this.
Base = declarative_base()

# Dependency to get a DB session. This will be used in our API routers.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()