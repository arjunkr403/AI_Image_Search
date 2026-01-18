import requests
import os
from fastapi import APIRouter 
#APIRouter is used to group routes (endpoints) in a modular way.

from app.services.db import get_db_connection,release_db_connection
from app.services.cache import redis_client

router=APIRouter() #router instance , creates a "mini FastAPI app"

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")  # set in Render env vars

@router.get("/health")
def health():
    #testing PostgreSQL
    try:
        connection=get_db_connection() #tries to connect
        release_db_connection(connection)
        db_status="OK"
    except:
        db_status="FAILED"
        
    #testing Redis
    try:
        redis_client.ping() #health check command
        redis_status="OK"
    except:
        redis_status="FAILED"
        
    #testing ML service 
    ml_status="NOT_CONFIGURED"
    if ML_SERVICE_URL:
        try:
            r = requests.get(f"{ML_SERVICE_URL}/health", timeout=2)
            ml_status = "OK" if r.status_code == 200 else "DOWN"
        except Exception:
            ml_status = "UNREACHABLE"

    return{
        "status":"running",
        "database":db_status,
        "redis":redis_status,
        "ml_service":ml_status,
    }