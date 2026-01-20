import uuid  # Used to generate unique IDs for filenames to avoid collisions
from typing import List
import json
import hashlib
import os
import tempfile
import requests

from app.services.cache import redis_client
from app.services.db import get_db_connection, release_db_connection
from app.services.r2 import upload_file
from app.config import settings

from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image  # verify files are real images


router = APIRouter(prefix="/upload", tags=["Upload"])

ML_SERVICE_URL = settings.ML_SERVICE_URL  # env var


@router.post("")
@router.post("/")
# Accepts an uploaded file from the client using multipart/form-data
# UploadFile allows streaming large files without loading them fully into memory
# File(...) means this field is required
async def upload_images(files: List[UploadFile] = File(...)):
    uploaded_results = []
    
    if not ML_SERVICE_URL:
        raise HTTPException(
        status_code=503,
        detail="ML service not configured"
    )

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
                    "SELECT id,filepath FROM images WHERE image_hash = %s",
                    (image_hash,),
                )
                existing = cur.fetchone()
                print(existing)
                if existing:
                    os.unlink(temp_file.name)

                    uploaded_results.append(
                        {
                            "image_id": existing["id"],
                            "duplicate": True,
                            "filename": file.filename,
                            "image_url": existing["filepath"],
                            "ml_status": "SKIPPED",
                        }   
                    )
                    continue

                # uploading to r2 (streaming)
                with open(temp_file.name, "rb") as f:  # opened temp_file in binary mode
                    upload_file(
                        file_obj=f,
                        key=r2_key,
                        content_type=file.content_type,
                    )

                # store r2 url in db
                file_url = f"{settings.R2_PUBLIC_URL}/{r2_key}"
                cur.execute(
                    """
                    INSERT INTO images (filename, filepath, image_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """,
                    (filename, file_url, image_hash),
                )
                image_id = cur.fetchone()["id"]  # getting id of inserted row
                conn.commit()

        except Exception as e:
            conn.rollback()
            raise

        finally:
            release_db_connection(conn)
            try:
                os.unlink(temp_file.name)
            except FileNotFoundError:
                pass

        # Calling ML service (async via HTTP)
        try:
            r = requests.post(
                f"{ML_SERVICE_URL}/embed",
                json={
                    "image_url": file_url,
                    "image_id": image_id,
                },
                timeout=60,
            )
            r.raise_for_status()
        except Exception as e:
            # IMPORTANT: backend upload succeeded, ML failed
            uploaded_results.append(
                {
                    "image_id": image_id,
                    "filename": filename,
                    "image_url": file_url,
                    "ml_status": "FAILED",
                }
            )
            continue

        # Cache upload metadata
        redis_client.set(f"image:{filename}", file_url)

        # Invalidate related caches
        redis_client.delete("dashboard:stats")
        redis_client.delete("search:history:50")

        uploaded_results.append(
            {
                "image_id": image_id,
                "filename": filename,
                "image_url": file_url,
                "ml_status": "OK",
            }
        )

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
