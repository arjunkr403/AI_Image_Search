import json
import os
import uuid
import hashlib
import aiofiles
import app.ml.faiss_index as faiss_store  # import module, not snapshot
import numpy as np
from pathlib import Path
from app.ml.embeddings import gen_img_embedding
from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client
from app.services.embedding_store import fetch_all_embeddings
from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/search", tags=["Search"])

UPLOAD_DIR = Path("/app/uploads")

@router.post("/")
async def search_similar_images(file: UploadFile = File(...), top_k: int = 5):
    # read uploaded image into bytes
    content = await file.read()
    
    # generate deterministic cache key from image content
    image_hash = hashlib.sha256(content).hexdigest()
    cache_key = f"search:{image_hash}:{top_k}"

    cached = redis_client.get(cache_key)
    if cached:
        print("Cache hit: returing cached searc results")
        return json.loads(cached)

    # cache miss : normal flow
    
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    temp_name = f"temp_{uuid.uuid4()}.jpg"
    temp_path = UPLOAD_DIR / temp_name

    try:
        async with aiofiles.open(temp_path, "wb") as out_file:
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to save uploaded image: {e}"
        )

    # generating CLIP embedding for the uploaded image

    try:
        query_embedding = gen_img_embedding(
            str(temp_path)
        )  # creates embedding for the given image path
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or unreadable image file")

    # load global FAISS index
    if not faiss_store.faiss_ready:
        raise HTTPException(status_code=400, detail="FAISS index not initialized. Upload images or reindex")

    # searching FAISS engine for nearest neighbours
    top_k = min(top_k, faiss_store.faiss_index.ntotal)
    try:
        # distances = Distance/similarity scores, shape -> (n_queries, k)
        # indices = Index positions of nearest vectors, shape -> (n_queries, k)
        # search() always needs =>{ vector, number_of_results}
        distances, indices = faiss_store.faiss_index.search(
            np.array([query_embedding]).astype("float32"),
            top_k,
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error during FAISS search")

    # Map FAISS results -> real image_ids

    results = []
    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            for score, idx in zip(distances[0], indices[0]):
                if idx>=len(faiss_store.faiss_ids):
                    continue
                image_id = faiss_store.faiss_ids[idx]
                cur.execute(
                    "SELECT filename,filepath FROM images WHERE id=%s", (image_id,)
                )
                row = cur.fetchone()
                if row:
                    filename = row["filename"]
                    url = f"/uploads/{filename}"

                    results.append(
                        {
                            "image_id": image_id,  # map FAISS index -> real image_id
                            "score": float(score),  # lower score = more similar
                            "filename": filename,
                            "url": url,
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
            os.remove(temp_path)
        except FileNotFoundError:
            pass

    # final response
    response = {"query_image": temp_name, "results": results}

    redis_client.setex(cache_key, 300, json.dumps(response))

    return response
    # High Order Overview

    # 1. save uploaded images(async)
    # 2. convert image -> embedding
    # 3. fetch stored embeddings from postgres
    # 4. Build FAISS index
    # 5. Run similarity search
    # 6. Map FAISS index -> real image ids


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
                        row["created_at"].strftime("%Y-%m-%d %H:%M:%S") if row["created_at"] else "N/A"
                    ),
                }
                for row in rows
            ]

            # default=str to make everything serializable
            redis_client.setex(cache_key, 300, json.dumps(history))

            return history
    finally:
        release_db_connection(conn)
