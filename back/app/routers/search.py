import json
import hashlib
import requests

from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client
from app.config import settings

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/search", tags=["Search"])

ML_SERVICE_URL = settings.ML_SERVICE_URL

@router.post("/")
async def search_similar_images(file: UploadFile = File(...), top_k: int = 5):
    
    if not ML_SERVICE_URL:
        raise HTTPException(
            status_code=503,
            detail="ML service not configured",
        )
    
    # read uploaded image into bytes
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large")
    
    # generate deterministic cache key from image content
    image_hash = hashlib.sha256(content).hexdigest()
    cache_key = f"search:{image_hash}:{top_k}"

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # cache miss : normal flow
    
    try:
        files = {
            "file": (file.filename, content, file.content_type),
        }
        r = requests.post(
            f"{ML_SERVICE_URL}/search",
            files=files,
            params={"top_k": top_k},
            timeout=60,
        )
        r.raise_for_status()
        ml_response = r.json()
        
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="ML search service unavailable",
        )

    results = ml_response.get("results")
    if not isinstance(results, list):
        raise HTTPException(
            status_code=502,
            detail="Invalid response from ML service",
        )
        
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO search_history (query_image_filename,results) VALUES (%s,%s)",
                (file.filename, json.dumps(results)),
            )
            conn.commit()

    except Exception:
        if conn:
            conn.rollback()  # rollback on error
        raise HTTPException(status_code=500, detail="Database operation failed.")

    finally:
        if conn:
            release_db_connection(conn)

    # final response
    response = {"query_image": file.filename, "results": results}

    redis_client.setex(cache_key, 300, json.dumps(response))

    return response


# Client image
#  → read bytes
#  → hash(bytes)
#  → Redis cache lookup
#    → hit → return
#    → miss:
#         → temp file
#         → embedding
#         → FAISS search
#         → DB fetch
#         → store history
#         → cache result
#         → return


@router.get("/history")
async def get_search_history(limit: int = 50):

    cache_key = f"search:history:{limit}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id,query_image_filename,results,created_at
                FROM search_history
                ORDER BY created_at DESC
                LIMIT %s;
                """,
                (limit,),
            )

            rows = cur.fetchall()

            history = [
                {
                    "id": row["id"],
                    "query_image": row["query_image_filename"],
                    "results": row["results"],
                    "time": (
                        row["created_at"].strftime("%Y-%m-%d %H:%M:%S")
                        if row["created_at"]
                        else "N/A"
                    ),
                }
                for row in rows
            ]
            
            redis_client.setex(cache_key, 300, json.dumps(history))

            return history
    finally:
        release_db_connection(conn)
