import json
import hashlib
import requests

from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client
from app.config import settings

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel
router = APIRouter(prefix="/search", tags=["Search"])

ML_SERVICE_URL = settings.ML_SERVICE_URL

class SearchRequest(BaseModel):
    image_url: str
    top_k: int = 5 


@router.post("/")
async def search_similar_images(req : SearchRequest):
    if not ML_SERVICE_URL:
        raise HTTPException(
            status_code=503,
            detail="ML service not configured",
        )

    # generate deterministic cache key from image content
    image_hash = hashlib.sha256(req.image_url.encode()).hexdigest()
    cache_key = f"search:{image_hash}:{req.top_k}"

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # cache miss : call ML service
    try:
        r = requests.post(
            f"{ML_SERVICE_URL}/search",
            json={
                "image_url": req.image_url,
                "top_k": req.top_k,
            },
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
                (req.image_url, json.dumps(results)),
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
    response = {"query_image": req.image_url, "results": results}

    redis_client.setex(cache_key, 300, json.dumps(response))

    return response


#  Client
#  → sends image_url + top_k (JSON)
#  → Backend /search
#       → hash(image_url)
#       → Redis cache lookup
#         → hit → return cached results
#         → miss:
#              → call ML service with image_url
#              → ML downloads image from R2
#              → C++ preprocess
#              → CLIP embedding
#              → FAISS similarity search
#              → return results
#       → store search history in DB
#       → cache response in Redis
#       → return results to client


@router.get("/history")
async def get_search_history(limit: int = 50):

    cache_key = f"search:history:limit:{limit}"
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
