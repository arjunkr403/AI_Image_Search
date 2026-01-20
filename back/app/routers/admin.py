import requests
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.services.db import get_db_connection, release_db_connection

router = APIRouter(prefix="/admin", tags=["Admin"])

ML_SERVICE_URL = settings.ML_SERVICE_URL


# 🔹 1. Trigger ML FAISS rebuild
@router.post("/reindex")
def reindex():
    if not ML_SERVICE_URL:
        raise HTTPException(status_code=503, detail="ML service not configured")

    try:
        r = requests.post(
            f"{ML_SERVICE_URL}/admin/reindex",
            timeout=300,  # reindex can be slow
        )
        r.raise_for_status()
        return {
            "status": "Reindex triggered",
            "ml_response": r.json(),
        }

    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"ML reindex failed: {e}",
        )


# 🔹 2. Provide all images to ML service
@router.get("/images")
def list_all_images():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, filepath
                FROM images
                ORDER BY id ASC
                """
            )
            rows = cur.fetchall()

            return {
                "images": [
                    {
                        "image_id": row["id"],
                        "image_url": row["filepath"],
                    }
                    for row in rows
                ]
            }
    finally:
        release_db_connection(conn)
