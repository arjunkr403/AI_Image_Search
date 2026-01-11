from contextlib import asynccontextmanager

from app.ml.faiss_index import load_faiss_index, rebuild_faiss_from_db
from app.routers import dashboard, health, search, upload, admin
from app.services.init_db import create_tables
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging

logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()  # create DB tables when app starts
    try:
        load_faiss_index()  # fast cache restore
        logger.info("FAISS loaded from cache")
    except Exception as e:
        logger.warning(f"FAISS cache load failed: {e}")
    warmup_faiss()  # authoritative rebuild

    yield  # app runs
    print("Shutting down...")
    # Startup code before the yield
    # Shutdown code after the yield


app = FastAPI(lifespan=lifespan)


def warmup_faiss():
    try:
        rebuild_faiss_from_db()
        logger.info("FAISS auto-warmed on startup")
    except Exception as e:
        logger.warning(f"FAISS warmup skipped: {e}")


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/uploads", StaticFiles(directory="/app/uploads"), name="uploads"
)  # creates a public url at /uploads


@app.get(
    "/"
)  # called 'decorator'attaches below function to the route defined in the decorator itself.
def home():
    return {"message": "Backend running!"}


app.include_router(health.router)
app.include_router(upload.router)
app.include_router(search.router)
app.include_router(dashboard.router)
app.include_router(admin.router)
# app.include_router(embedding.router)
