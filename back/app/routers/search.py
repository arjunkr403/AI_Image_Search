import json
import os
import uuid
import hashlib
import numpy as np
import tempfile

import app.ml.faiss_index as faiss_store  # import module, not snapshot
from app.ml.embeddings import gen_img_embedding
from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client
from app.services.embedding_store import fetch_all_embeddings
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/search", tags=["Search"])


@router.post("/")
async def search_similar_images(file: UploadFile = File(...), top_k: int = 5):
    # read uploaded image into bytes
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "File too large")
    # generate deterministic cache key from image content
    image_hash = hashlib.sha256(content).hexdigest()
    # searching FAISS engine for nearest neighbours
    if faiss_store.faiss_ready:
        top_k = min(top_k, faiss_store.faiss_index.ntotal)
    cache_key = f"search:{image_hash}:{top_k}"

    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # cache miss : normal flow
    suffix = os.path.splitext(file.filename)[-1] or ".jpg"
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(content)
            temp_path = temp_file.name
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded image: {e}"
        )

    # generating CLIP embedding for the uploaded image
    try:
        query_embedding = gen_img_embedding(temp_path)
    except Exception:
        os.unlink(temp_path)
        raise HTTPException(status_code=400, detail="Invalid or unreadable image file")

    # load global FAISS index
    if not faiss_store.faiss_ready or faiss_store.faiss_index.ntotal == 0:
        os.unlink(temp_path)
        raise HTTPException(
            status_code=400,
            detail="FAISS index not initialized. Upload images or reindex",
        )

    try:
        # distances = Distance/similarity scores, shape -> (n_queries, k)
        # indices = Index positions of nearest vectors, shape -> (n_queries, k)
        # search() always needs =>{ vector, number_of_results}
        distances, indices = faiss_store.faiss_index.search(
            np.array([query_embedding]).astype("float32"),
            top_k,
        )
    except Exception:
        os.unlink(temp_path)
        raise HTTPException(status_code=500, detail="Error during FAISS search")

    # Map FAISS results -> real image_ids

    results = []
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            for score, idx in zip(distances[0], indices[0]):
                if idx >= len(faiss_store.faiss_ids):
                    continue
                image_id = faiss_store.faiss_ids[idx]
                cur.execute(
                    "SELECT filename,filepath FROM images WHERE id=%s", (image_id,)
                )
                row = cur.fetchone()
                if row:
                    results.append(
                        {
                            "image_id": image_id,  # map FAISS index -> real image_id
                            "score": float(score),  # lower score = more similar
                            "filename": row["filename"],
                            "url": row["filepath"],
                        }
                    )

            cur.execute(
                "INSERT INTO search_history (query_image_filename,results) VALUES (%s,%s)",
                (file.filename, json.dumps(results)),
            )
            conn.commit()

    except Exception as e:
        print(f"Database error: {e}")
        if conn:
            conn.rollback()  # rollback on error
        raise HTTPException(status_code=500, detail="Database operation failed.")

    finally:
        if conn:
            release_db_connection(conn)
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass

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

            # default=str to make everything serializable
            redis_client.setex(cache_key, 300, json.dumps(history))

            return history
    finally:
        release_db_connection(conn)
