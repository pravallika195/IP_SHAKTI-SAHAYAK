"""Database initialization and connectivity for IP-SAKTI Sahayak.

Manages MySQL 8 database connection via SQLAlchemy, ensures InnoDB and utf8mb4,
and provides session handling.
"""
from __future__ import annotations
import logging
import os
import pymysql
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine, text

from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_USER,
    MYSQL_PASSWORD,
    MYSQL_DATABASE,
    MYSQL_CHARSET
)

logger = logging.getLogger(__name__)

# Flask-SQLAlchemy instance
db = SQLAlchemy()


def get_database_uri() -> str:
    """Builds standard MySQL SQLAlchemy URI from environment credentials."""
    user = MYSQL_USER
    pwd = f":{MYSQL_PASSWORD}" if MYSQL_PASSWORD else ""
    return f"mysql+pymysql://{user}{pwd}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}?charset={MYSQL_CHARSET}"


def ensure_database_exists():
    """Connects to MySQL server without selecting DB and creates the database if it does not exist."""
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            charset=MYSQL_CHARSET,
            autocommit=True
        )
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                f"CHARACTER SET {MYSQL_CHARSET} COLLATE {MYSQL_CHARSET}_unicode_ci;"
            )
            logger.info("Verified or created database `%s` on MySQL %s:%s", MYSQL_DATABASE, MYSQL_HOST, MYSQL_PORT)
        conn.close()
    except Exception as exc:
        logger.error("Could not ensure database `%s` exists: %s", MYSQL_DATABASE, exc)
        raise


def init_db(app):
    """Initializes SQLAlchemy with the Flask application."""
    app.config["SQLALCHEMY_DATABASE_URI"] = get_database_uri()
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 10,
        "max_overflow": 20
    }
    db.init_app(app)

