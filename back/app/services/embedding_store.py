import json
from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client


def fetch_all_embeddings():
    cache_key = "embeddings:all"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT image_id,vector FROM embeddings")
            data = cur.fetchall()  # fetch all rows

            redis_client.setex(cache_key, 500, json.dumps(data))
            return data
    finally:
        release_db_connection(conn)
