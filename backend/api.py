from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import asyncio
import json
from redis.asyncio import Redis
from asyncpg import create_pool

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "database": os.getenv("POSTGRES_DB"),
    "host": "timescaledb",
    "port": 5432,
    "min_size": 1,
    "max_size": 10,
}

# FastAPI instance
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://hack.kevinlockburner.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for resources
DB_POOL = None
REDIS_CLIENT = None

# Lifespan events
@app.on_event("startup")
async def startup():
    global DB_POOL, REDIS_CLIENT
    try:
        # Initialize database pool
        DB_POOL = await create_pool(**DB_CONFIG)

        # Initialize Redis client
        REDIS_CLIENT = Redis(host="172.17.0.1", port=6379, decode_responses=True)
        await REDIS_CLIENT.ping()  # Test Redis connection
        print("Redis connection established.")
    except Exception as e:
        print(f"Error during startup: {e}")
        raise RuntimeError("Failed to initialize resources during startup.")

@app.on_event("shutdown")
async def shutdown():
    global DB_POOL, REDIS_CLIENT
    try:
        # Close database pool
        if DB_POOL:
            await DB_POOL.close()
        # Close Redis connection
        if REDIS_CLIENT:
            await REDIS_CLIENT.close()
        print("Resources cleaned up successfully.")
    except Exception as e:
        print(f"Error during shutdown: {e}")

# Pydantic model for attack logs
class AttackLog(BaseModel):
    ip_address: str
    timestamp: str
    port: int
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# API endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Server Attack Map API"}

@app.get("/logs/", response_model=List[AttackLog])
async def read_logs():
    try:
        async with DB_POOL.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
                FROM failed_logins
                ORDER BY timestamp DESC
                """
            )
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {e}")

@app.get("/maplogs/", response_model=List[AttackLog])
async def read_map_logs():
    try:
        # Check Redis cache first
        cached_data = await REDIS_CLIENT.get("maplogs")
        if cached_data:
            return json.loads(cached_data)

        # Query database if cache is empty
        async with DB_POOL.acquire() as conn:
            rows = await conn.fetch(
                """
                WITH ranked_entries AS (
                    SELECT 
                        ip_address, 
                        timestamp, 
                        port, 
                        city, 
                        region, 
                        country, 
                        latitude, 
                        longitude,
                        ROW_NUMBER() OVER (PARTITION BY city ORDER BY timestamp DESC) AS rank
                    FROM failed_logins
                    WHERE city IS NOT NULL
                )
                SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
                FROM ranked_entries
                WHERE rank <= 2
                ORDER BY timestamp DESC
                LIMIT 100;
                """
            )
            maplogs = [dict(row) for row in rows]
            await REDIS_CLIENT.set("maplogs", json.dumps(maplogs), ex=60)  # Cache for 60 seconds
            return maplogs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching map logs: {e}")

@app.websocket("/ws/maplogs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            cached_data = await REDIS_CLIENT.get("maplogs")
            if cached_data:
                await websocket.send_json({"type": "logs", "data": json.loads(cached_data)})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
