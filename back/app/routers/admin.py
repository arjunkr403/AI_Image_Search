import requests
from fastapi import APIRouter, HTTPException

from app.config import settings

router = APIRouter(prefix="/admin", tags=["Admin"])

ML_SERVICE_URL = settings.ML_SERVICE_URL


@router.post("/reindex")
def reindex():
    if not ML_SERVICE_URL:
        raise HTTPException(
            status_code=503,
            detail="ML service not configured",
        )

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
