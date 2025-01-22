from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
import asyncio
import asyncpg
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
    "max_size": 20,  # Adjust as needed
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

# Global variable for connection pool
DB_POOL = None

# Lifespan events
@app.on_event("startup")
async def startup():
    global DB_POOL
    try:
        # Initialize database connection pool
        DB_POOL = await create_pool(**DB_CONFIG)
        print("Database connection pool established.")
    except Exception as e:
        print(f"Error during startup: {e}")
        raise RuntimeError("Failed to initialize resources during startup.")

@app.on_event("shutdown")
async def shutdown():
    global DB_POOL
    try:
        # Close database pool
        if DB_POOL:
            await DB_POOL.close()
            print("Database connection pool closed.")
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

# Retry logic for database queries
async def fetch_with_retry(pool, query, params=None, retries=3, delay=2):
    for attempt in range(retries):
        try:
            async with pool.acquire() as conn:
                if params:
                    return await conn.fetch(query, *params)
                return await conn.fetch(query)
        except asyncpg.exceptions.TooManyConnectionsError as e:
            print(f"Connection error: {e}")
            if attempt < retries - 1:
                await asyncio.sleep(delay)
            else:
                raise

# API endpoints
@app.get("/")
def read_root():
    return {"message": "Welcome to the Server Attack Map API"}

@app.get("/logs/", response_model=List[AttackLog])
async def read_logs(limit: int = 100, offset: int = 0):
    query = """
        SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
        FROM failed_logins
        ORDER BY timestamp DESC
    """
    try:
        rows = await fetch_with_retry(DB_POOL, query, params=(limit, offset))
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {e}")

@app.get("/charts/top-countries/")
async def top_attack_sources(limit: int = 10):
    query = """
        SELECT country, COUNT(*) AS count
        FROM failed_logins
        GROUP BY country
        ORDER BY count DESC
        LIMIT $1
    """
    try:
        rows = await fetch_with_retry(DB_POOL, query, params=(limit,))
        return [{"country": row["country"] or "Unknown", "count": row["count"]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top attack sources: {e}")


@app.get("/charts/attack-trends/")
async def attack_trends():
    query = """
        SELECT DATE(timestamp) AS attack_date, COUNT(*) AS count
        FROM failed_logins
        GROUP BY attack_date
        ORDER BY attack_date
    """
    try:
        rows = await fetch_with_retry(DB_POOL, query)
        return [{"date": str(row["attack_date"]), "count": row["count"]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attack trends: {e}")


@app.get("/charts/time-of-day/")
async def attack_distribution_by_time():
    query = """
        SELECT EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS count
        FROM failed_logins
        GROUP BY hour
        ORDER BY hour
    """
    try:
        rows = await fetch_with_retry(DB_POOL, query)
        # Fill missing hours with 0 counts
        hour_data = {int(row["hour"]): row["count"] for row in rows}
        return [{"hour": f"{hour}:00 - {hour + 1}:00", "count": hour_data.get(hour, 0)} for hour in range(24)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching time of day distribution: {e}")


@app.get("/maplogs/", response_model=List[AttackLog])
async def read_map_logs():
    query = """
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
    try:
        rows = await fetch_with_retry(DB_POOL, query)
        return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching map logs: {e}")

@app.websocket("/ws/maplogs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            query = """
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
            try:
                rows = await fetch_with_retry(DB_POOL, query)
                logs = [dict(row) for row in rows]
                await websocket.send_json({"type": "logs", "data": logs})
            except Exception as e:
                print(f"Database error: {e}")
            
            await asyncio.sleep(15)  # Update every 15 seconds
    except WebSocketDisconnect:
        print("WebSocket disconnected.")
