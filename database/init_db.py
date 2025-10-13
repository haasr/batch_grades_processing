#!/usr/bin/env python3
"""
Database initialization script.
Run this to create all tables.
"""

from .connection import engine, Base, DATABASE_URL
from .models import Student, Course, GradeSnapshot, StudentGrade
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database(drop_existing=False):
    """
    Initialize the database by creating all tables.
    
    Args:
        drop_existing (bool): If True, drop all existing tables first (DANGER!)
    """
    logger.info(f"Initializing database at: {DATABASE_URL}")
    
    if drop_existing:
        logger.warning("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("Tables dropped.")
    
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully!")
    
    # Print created tables
    logger.info("Created tables:")
    for table in Base.metadata.sorted_tables:
        logger.info(f"  - {table.name}")


def verify_database():
    """Verify database connection and tables exist"""
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info(f"Database contains {len(tables)} tables:")
    for table in tables:
        logger.info(f"  - {table}")
    
    expected_tables = {'students', 'courses', 'grade_snapshots', 'student_grades'}
    missing_tables = expected_tables - set(tables)
    
    if missing_tables:
        logger.error(f"Missing tables: {missing_tables}")
        return False
    
    logger.info("All expected tables exist!")
    return True


if __name__ == '__main__':
    import sys
    
    # Check for --drop flag
    drop = '--drop' in sys.argv
    
    if drop:
        confirm = input("⚠️  This will DELETE ALL DATA. Are you sure? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    init_database(drop_existing=drop)
    verify_database()