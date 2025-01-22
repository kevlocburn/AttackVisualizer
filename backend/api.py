from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import aioredis
import json
from asyncpg import create_pool

# Load environment variables from .env
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "database": os.getenv("POSTGRES_DB"),
    "host": "timescaledb",
    "port": 5432,
    "min_size": 1,  # Minimum connections in the pool
    "max_size": 10, # Maximum connections in the pool
}

# FastAPI instance
app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://hack.kevinlockburner.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model
class AttackLog(BaseModel):
    ip_address: str
    timestamp: str
    port: int
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# Global variables for database pool and Redis client
DB_POOL = None
REDIS_CLIENT = None

# Initialize connection pool and Redis on startup
@app.on_event("startup")
async def startup():
    global DB_POOL, REDIS_CLIENT
    DB_POOL = await create_pool(**DB_CONFIG)
    REDIS_CLIENT = await aioredis.create_redis_pool("redis://localhost", encoding="utf-8")

# Close connections on shutdown
@app.on_event("shutdown")
async def shutdown():
    await DB_POOL.close()
    REDIS_CLIENT.close()
    await REDIS_CLIENT.wait_closed()

# Root endpoint
@app.get("/")
def read_root():
    return {"message": "Welcome to the Server Attack Map API"}

# Fetch all logs
@app.get("/logs/", response_model=List[AttackLog])
async def read_logs():
    try:
        async with DB_POOL.acquire() as conn:
            rows = await conn.fetch("""
                SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
                FROM failed_logins
                ORDER BY timestamp DESC
            """)
            logs = [dict(row) for row in rows]
            return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {e}")

# Fetch map logs with caching
@app.get("/maplogs/", response_model=List[AttackLog])
async def read_map_logs():
    try:
        # Check cache first
        cached_data = await REDIS_CLIENT.get("maplogs")
        if cached_data:
            return json.loads(cached_data)  # Convert string to Python object

        # Query the database if not in cache
        async with DB_POOL.acquire() as conn:
            rows = await conn.fetch("""
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
            """)
            maplogs = [dict(row) for row in rows]
            # Cache the result
            await REDIS_CLIENT.set("maplogs", str(maplogs), expire=60)  # Cache for 60 seconds
            return maplogs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching map logs: {e}")

# WebSocket endpoint
@app.websocket("/ws/maplogs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            cached_data = await REDIS_CLIENT.get("maplogs")
            if cached_data:
                await websocket.send_json({"type": "logs", "data": eval(cached_data)})
            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        print("WebSocket disconnected")
