from app.services.db import get_db_connection, release_db_connection
from app.services.cache import redis_client
from fastapi import APIRouter
import json

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
async def get_dashboard_stats():
    cache_key = "dashboard:stats"

    cached = redis_client.get(cache_key)
    if cached:
        # Deserializes a JSON string → Python object
        return json.loads(cached)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Total Images
            cur.execute("SELECT COUNT(*) as count FROM images;")
            image_count = cur.fetchone()["count"]

            # 2. Recent Uploads (Limit 5)
            cur.execute(
                """
                SELECT id, filename, uploaded_at
                FROM images
                ORDER BY uploaded_at DESC
                LIMIT 5;
            """
            )
            recent_uploads = cur.fetchall()

            # Format uploads
            formatted_uploads = []
            for row in recent_uploads:
                formatted_uploads.append(
                    {
                        "id": row["id"],
                        "action": "Uploaded Image",
                        "details": row["filename"],
                        "time": (
                            row["uploaded_at"].strftime("%Y-%m-%d %H:%M")
                            if row["uploaded_at"]
                            else "N/A"
                        ),
                        "type": "upload",
                    }
                )

            # get search count
            cur.execute("SELECT COUNT(*) as count FROM search_history;")
            search_count = cur.fetchone()["count"]

            response = {
                "total_images": image_count,
                "total_searches": search_count,
                "system_status": "Active",
                "recent_activity": formatted_uploads,
            }
            #stores the value and sets expiration time
            # Serializes a Python object → JSON string
            redis_client.setex(cache_key,300,json.dumps(response))
            return response
    finally:
        release_db_connection(conn)
