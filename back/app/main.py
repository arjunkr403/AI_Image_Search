from contextlib import asynccontextmanager
import logging

from app.routers import dashboard, health, search, upload, admin
from app.services.init_db import create_tables

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


logger = logging.getLogger("uvicorn")

@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # Initialize DB tables when app starts
    create_tables()  
    logger.info("Database initialized")
    
    yield  # app runs
    
    logger.info("Shutting down...")
    
    # Startup code before the yield
    # Shutdown code after the yield


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
