"""Database initialization and schema migration script for IP-SAKTI Sahayak.

Executes schema creation across MySQL 8 with InnoDB and utf8mb4.
"""
import sys
import logging
from flask import Flask
from config import BASE_DIR
from database import db, ensure_database_exists, init_db
import models  # Ensure all 8 models are loaded

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migrations():
    logger.info("Verifying MySQL database and creating tables...")
    ensure_database_exists()

    app = Flask(__name__)
    init_db(app)

    with app.app_context():
        # Create all tables if they don't exist
        db.create_all()
        logger.info("All 8 MySQL tables successfully verified/created with InnoDB and utf8mb4.")

        # Verify tables in database
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        logger.info("Tables found in database: %s", tables)
        expected = [
            "users", "innovations", "innovation_versions", "innovation_documents",
            "analysis_runs", "chat_threads", "chat_messages", "chat_message_sources"
        ]
        missing = [t for t in expected if t not in tables]
        if missing:
            logger.error("Missing expected tables: %s", missing)
            sys.exit(1)
        else:
            logger.info("All %d required tables are present!", len(expected))

if __name__ == "__main__":
    run_migrations()

