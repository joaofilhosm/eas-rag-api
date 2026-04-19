"""Database module EAS - PostgreSQL + pgvector."""
from .database import db, get_database, get_db, Database

__all__ = ["db", "get_database", "get_db", "Database"]