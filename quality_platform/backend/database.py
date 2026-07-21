from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Use absolute path for SQLite database to avoid issues with working directory
_db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(_db_dir, exist_ok=True)
_db_path = os.path.join(_db_dir, 'quality_news.db')
DATABASE_URL = f"sqlite:///{_db_path}"

# Create engine with connect_args for SQLite to prevent thread errors
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()