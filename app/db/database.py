import logging
from typing import Any, Dict
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global connection pool
connection_pool = None


def setup_db_pool():
    """Initialize the database connection pool."""
    global connection_pool
    
    if connection_pool is not None:
        logger.info("DB connection pool already initialized")
        return connection_pool
    
    try:
        connection_pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=settings.PG_DB_HOST,
            port=settings.PG_DB_PORT,
            dbname=settings.PG_DB_NAME,
            user=settings.PG_DB_USER,
            password=settings.PG_DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        logger.info("Database connection pool initialized successfully")
        return connection_pool
    except Exception as e:
        logger.error(f"Error initializing database connection pool: {e}")
        raise


def get_db_pool():
    """Get the database connection pool, initializing it if necessary."""
    global connection_pool
    if connection_pool is None:
        connection_pool = setup_db_pool()
    return connection_pool


@contextmanager
def get_db_connection():
    """
    Context manager to get a database connection from the pool.
    
    Example:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM candidates LIMIT 1")
                result = cursor.fetchone()
    """
    pool = get_db_pool()
    conn = None
    
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise
    finally:
        if conn:
            # Important: put the connection back in the pool
            pool.putconn(conn)


def execute_query(query: str, params: tuple = None, fetchone: bool = False) -> Dict[str, Any]:
    """
    Execute a database query and return the results.
    
    Args:
        query: SQL query to execute
        params: Query parameters
        fetchone: Whether to fetch just one result
        
    Returns:
        Query results as a dictionary
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                cursor.execute(query, params)
                
                if fetchone:
                    return cursor.fetchone()
                return cursor.fetchall()
            except Exception as e:
                logger.error(f"Query execution error: {str(e)}")
                conn.rollback()
                raise
            finally:
                if not fetchone and not query.strip().upper().startswith("SELECT"):
                    conn.commit()


def close_db_pool():
    """Close the database connection pool."""
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        connection_pool = None
        logger.info("Database connection pool closed")