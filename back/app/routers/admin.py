from app.ml.faiss_index import rebuild_faiss_from_db
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/reindex")
def reindex():
    rebuild_faiss_from_db()
    return {"status": "FAISS rebuilt"}
