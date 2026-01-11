# psycopg2 is the PostgreSQL adapter for Python
import psycopg2
import time
# SimpleConnectionPool creates a reusable pool of DB connections
from psycopg2.pool import SimpleConnectionPool

# RealDictCursor returns rows as dictionaries
from psycopg2.extras import RealDictCursor

# Loads DB settings from .env
from app.config import settings

for _ in range(10):
# maintain a limited number of open DB connections
    try:
        pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host=settings.POSTGRES_HOST,
    database=settings.POSTGRES_DB,
    user=settings.POSTGRES_USER,
    password=settings.POSTGRES_PASSWORD,
    cursor_factory=RealDictCursor
)
        break
    except psycopg2.OperationalError:
        time.sleep(2)

# Borrow a connection from the pool.
# FastAPI will call this before executing an endpoint.
def get_db_connection():
    return pool.getconn()

# Return the connection back to the pool.
# FastAPI calls this after the endpoint finishes.
def release_db_connection(conn):
    pool.putconn(conn)
