import json
import hashlib
import requests

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client
from app.config import settings

router = APIRouter(prefix="/search", tags=["Search"])

ML_SERVICE_URL = settings.ML_SERVICE_URL


class SearchRequest(BaseModel):
    image_url: str
    top_k: int = 5


@router.post("/")
async def search_similar_images(req: SearchRequest):
    if not ML_SERVICE_URL:
        raise HTTPException(status_code=503, detail="ML service not configured")

    # Cache key (stable for same query image)
    image_hash = hashlib.sha256(req.image_url.encode()).hexdigest()
    cache_key = f"search:{image_hash}:{req.top_k}"

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # ---- Call ML service ----
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
        raise HTTPException(status_code=502, detail="ML search service unavailable")

    results = ml_response.get("results")
    if not isinstance(results, list):
        raise HTTPException(status_code=502, detail="Invalid ML response")

    if not results:
        return {"query_image": req.image_url, "results": []}

    image_ids = [r["image_id"] for r in results]

    # ---- Fetch DB metadata ----
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get query image id (to exclude self match)
            cur.execute(
                "SELECT id FROM images WHERE filepath = %s",
                (req.image_url,),
            )
            row = cur.fetchone()
            query_image_id = row["id"] if row else None

            # Fetch result images
            cur.execute(
                """
                SELECT id, filename, filepath
                FROM images
                WHERE id = ANY(%s)
                """,
                (image_ids,),
            )
            rows = cur.fetchall()

            image_map = {
                row["id"]: {
                    "image_url": row["filepath"],
                    "filename": row["filename"],
                }
                for row in rows
            }
    finally:
        release_db_connection(conn)

    # ---- Merge ML + DB (exclude query image) ----
    enriched_results = []
    for r in results:
        if r["image_id"] == query_image_id:
            continue  # remove self-match

        meta = image_map.get(r["image_id"])
        if not meta:
            continue

        enriched_results.append(
            {
                "image_id": r["image_id"],
                "score": r["score"],           # cosine similarity
                "image_url": meta["image_url"],
                "filename": meta["filename"],
            }
        )
    enriched_results.sort(key=lambda x: x["score"], reverse=True)
    response = {
        "query_image": req.image_url,
        "results": enriched_results,
    }

    redis_client.setex(cache_key, 300, json.dumps(response))
    return response


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
                SELECT id, query_image_filename, results, created_at
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
