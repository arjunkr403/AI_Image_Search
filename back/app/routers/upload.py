# HTTPException Used to return custom error responses
import uuid  # Used to generate unique IDs for filenames to avoid collisions
from typing import List
import json
import hashlib
import numpy as np
import os
import tempfile

import app.ml.faiss_index as faiss_store
from app.ml.embeddings import gen_img_embedding
from app.services.cache import redis_client
from app.services.db import get_db_connection, release_db_connection
from app.services.r2 import upload_file
from app.config import settings

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image  # verify files are real images


router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/")
# Accepts an uploaded file from the client using multipart/form-data
# UploadFile allows streaming large files without loading them fully into memory
# File(...) means this field is required
async def upload_images(files: List[UploadFile] = File(...)):
    uploaded_results = []

    for file in files:
        # validating file type
        if file.content_type not in [
            "image/png",
            "image/jpg",
            "image/jpeg",
        ]:  # Only allow PNG or JPEG images
            # For batch, we could skip or raise. Keeping strict for now.
            raise HTTPException(
                status_code=400, detail=f"Invalid file type for {file.filename}"
            )  # If someone uploads a PDF, EXE, ZIP → return HTTP 400

        # Validating actual image
        try:
            img = Image.open(file.file)
            img.verify()  # Ensures the file is a real image
            file.file.seek(0)  # Reset pointer back to start after verification
        except Exception:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file {file.filename} is not a valid image",
            )

        # create unique name
        file_id = str(uuid.uuid4())
        extension = file.filename.rsplit(".", 1)[
            -1
        ].lower()  # extract original extension
        filename = f"{file_id}.{extension}"
        r2_key = f"images/{filename}"

        # stream+ hash file
        hasher = hashlib.sha256()
        temp_file = tempfile.NamedTemporaryFile(
            delete=False
        )  # delete=False so the file persists on disk after closing (required for boto3 to reopen it)

        try:
            while chunk := await file.read(1024 * 1024):  # reads 1MB chunks
                hasher.update(chunk)
                temp_file.write(chunk)
        except Exception as e:
            raise HTTPException(500, f"Failed to save file {file.filename}:{e}")
        finally:
            temp_file.close()
        # Hash is computed incrementally over the full byte stream:
        # hash(image_bytes) == hash(chunk1 || chunk2 || ...)
        image_hash = hasher.hexdigest()

        conn = get_db_connection()
        try:
            with conn.cursor() as cur:

                cur.execute(
                    "SELECT id FROM images WHERE image_hash = %s",
                    (image_hash,),
                )
                existing = cur.fetchone()
                if existing:
                    os.unlink(temp_file.name)

                    uploaded_results.append(
                        {
                            "image_id": existing["id"],
                            "duplicate": True,
                            "filename": file.filename,
                        }
                    )
                    continue
                #uploading to r2 (streaming)
                with open (temp_file.name,"rb") as f: #opened temp_file in binary mode
                    upload_file(
                        file_obj=f,
                        key=r2_key,
                        content_type=file.content_type,
                    )
                    
                #store r2 url in db
                file_url = f"{settings.R2_PUBLIC_URL}/{r2_key}"
                cur.execute(
                    """
                    INSERT INTO images (filename, filepath,image_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """,
                    (filename, file_url, image_hash),
                )
                image_id = cur.fetchone()["id"]  # getting id of inserted row
                conn.commit()

            vector = gen_img_embedding(temp_file.name)

            with conn.cursor() as cur:
                cur.execute(
                    """
                        INSERT INTO embeddings (image_id, vector)
                        VALUES (%s, %s)
                        ON CONFLICT (image_id) DO UPDATE
                        SET vector = EXCLUDED.vector;
                    """,
                    (image_id, vector),
                )
                conn.commit()
                # updating FAISS index in real time
                # ensure FAISS is loaded
            if not faiss_store.faiss_ready:
                faiss_store.load_faiss_index()
            if faiss_store.faiss_ready:
                vector_np = np.array([vector], dtype="float32")
                faiss_store.faiss_index.add(vector_np)  # add new embedding to index
                faiss_store.faiss_ids.append(image_id)  # maintain mapping

        except Exception as e:
            conn.rollback()
            raise

        finally:
            release_db_connection(conn) 
            try:
                os.unlink(temp_file.name)
            except FileNotFoundError:
                pass
        uploaded_results.append(
            {
                "image_id": image_id,
                "filename": filename,
                "url": file_url,
            }
        )
        # Cache upload metadata
        redis_client.set(f"image:{filename}", file_url)
        # Invalidate related caches
        redis_client.delete("dashboard:stats")
        redis_client.delete("embeddings:all")
        redis_client.delete("search:history:50")

    # persisting faiss_store once per batch
    faiss_store.save_faiss()

    for key in redis_client.scan_iter("upload:history:*"):
        redis_client.delete(key)
    return {"message": "Images uploaded successfully", "uploaded": uploaded_results}

# Browser
#  → FastAPI
#    → stream file in chunks
#    → hash while streaming
#    → temporary file (short-lived)
#    → upload to Cloudflare R2
#    → generate embedding
#    → store R2 URL in DB
#  → Frontend loads image directly from R2

@router.get("/history")
async def get_upload_history(limit: int = 50):
    cache_key = f"upload:history:{limit}"
    cached = redis_client.get(cache_key)

    if cached:
        return json.loads(cached)

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id ,filename,uploaded_at
                FROM images
                ORDER BY uploaded_at DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()
            history = []
            for row in rows:
                history.append(
                    {
                        "id": row["id"],
                        "filename": row["filename"],
                        "time": (
                            row["uploaded_at"].strftime("%Y-%m-%d %H:%M:%S")
                            if row["uploaded_at"]
                            else "N/A"
                        ),
                        "status": "Success",
                    }
                )
            redis_client.setex(cache_key, 120, json.dumps(history, default=str))
            return history
    finally:
        release_db_connection(conn)
