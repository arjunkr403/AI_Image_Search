# HTTPException Used to return custom error responses
import uuid  # Used to generate unique IDs for filenames to avoid collisions
from typing import List
import json
import os
import hashlib
import aiofiles  # Async file saving
import app.ml.faiss_index as faiss_store
import numpy as np
from pathlib import Path
from app.ml.embeddings import gen_img_embedding
from app.services.cache import redis_client
from app.services.db import get_db_connection, release_db_connection
from fastapi import APIRouter, File, HTTPException, UploadFile
from PIL import Image  # verify files are real images

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = Path("/app/uploads")



@router.post("/")
# Accepts an uploaded file from the client using multipart/form-data
# UploadFile allows streaming large files without loading them fully into memory
# File(...) means this field is required
async def upload_images(files: List[UploadFile] = File(...)):
    uploaded_results = []
    
    # validating file type
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
        extension = file.filename.rsplit(".",1)[-1].lower()  # extract original extension
        filename = f"{file_id}.{extension}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        # defining where file will store in backend
        filepath = str(UPLOAD_DIR/filename)

        # aiofiles saves files without blocking other requests
        hasher=hashlib.sha256()
        
        try:
            async with aiofiles.open(filepath,"wb") as buffer:
                # ':=' ->  called walrus operator
                # equivalent to -> while True:
                                        # chunk=await file.read(1024*1024)
                                        # if not chunk:
                                        #     break
                while chunk:= await file.read(1024*1024):
                    hasher.update(chunk)
                    await buffer.write(chunk)
        except Exception as e:
            raise HTTPException(500,f"Failed to save file {file.filename}:{e}")

        image_hash=hasher.hexdigest()
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                
                cur.execute(
                    "SELECT id FROM images WHERE image_hash = %s",(
                        image_hash,),
                    )
                existing=cur.fetchone()
                if existing:
                    os.remove(filepath)
                    
                    uploaded_results.append({
                    "image_id": existing["id"],
                    "duplicate": True,
                    "filename": file.filename,
                    })
                    continue
                cur.execute(
                    """
                    INSERT INTO images (filename, filepath,image_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                """,
                    (filename, filepath, image_hash),
                )
                image_id = cur.fetchone()["id"]  # getting id of inserted row
                conn.commit()

            vector = gen_img_embedding(filepath)

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
            if "unique_image_hash" in str(e):
                if os.path.exists(filepath):
                    os.remove(filepath)
                    
                uploaded_results.append({
                "duplicate": True,
                "filename": file.filename,
                })
                
                continue
            
            raise
        
        finally:
            release_db_connection(conn)  # IMPORTANT

        uploaded_results.append(
            {
                "image_id": image_id,
                "filename": filename,
                "path": filepath,
            }
        )
        # Cache upload metadata
        redis_client.set(f"image:{filename}", filepath)
        # Invalidate related caches
        redis_client.delete("dashboard:stats")
        redis_client.delete("embeddings:all")
        redis_client.delete("search:history:50")

    #persisting faiss_store once per batch
    faiss_store.save_faiss()
    
    for key in redis_client.scan_iter("upload:history:*"):
        redis_client.delete(key)
    return {"message": "Images uploaded successfully", "uploaded": uploaded_results}


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
