from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
CURRENT_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent
load_dotenv((CURRENT_DIR / '.env').as_posix())

# Create base class for models
Base = declarative_base()

# Database configuration
DB_TYPE = os.getenv('DB_TYPE', 'sqlite')  # 'sqlite' or 'postgresql'

if DB_TYPE == 'postgresql':
    # PostgreSQL connection
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'grades_db')
    
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv('DB_ECHO', 'False') == 'True',  # Set to True for SQL logging
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )
else:
    # SQLite connection (default)
    db_path = CURRENT_DIR / 'grades.db'
    DATABASE_URL = f"sqlite:///{db_path}"
    
    engine = create_engine(
        DATABASE_URL,
        echo=os.getenv('DB_ECHO', 'False') == 'True',
        connect_args={"check_same_thread": False},  # Needed for SQLite with multiple threads
        poolclass=StaticPool
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    """
    Get a database session. Use as context manager:
    
    with get_db_session() as session:
        # do work
        session.commit()
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def get_db():
    """Get a database session (for non-context manager usage)"""
    return SessionLocal()