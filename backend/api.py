from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables from .env
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "timescaledb",
    "port": 5432,
}

# FastAPI instance
app = FastAPI()

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


@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to the Server Attack Map API"}

@app.get("/logs/", response_model=List[AttackLog])
def read_logs():
    """Fetch all logs from the database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
            FROM failed_logins
            ORDER BY timestamp DESC;
        """)
        rows = cursor.fetchall()

        logs = [
            AttackLog(
                ip_address=row[0],
                timestamp=row[1].strftime("%Y-%m-%d %H:%M:%S"),
                port=row[2],
                city=row[3],
                region=row[4],
                country=row[5],
                latitude=row[6],
                longitude=row[7],
            )
            for row in rows
        ]

        cursor.close()
        conn.close()
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {e}")

@app.get("/maplogs/", response_model=List[AttackLog])
def read_map_logs():
    """Fetch last 100 logs with max 2 repeating cities."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
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
        rows = cursor.fetchall()

        maplogs = [
            AttackLog(
                ip_address=row[0],
                timestamp=row[1].strftime("%Y-%m-%d %H:%M:%S"),
                port=row[2],
                city=row[3],
                region=row[4],
                country=row[5],
                latitude=row[6],
                longitude=row[7],
            )
            for row in rows
        ]

        cursor.close()
        conn.close()
        return maplogs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching map logs: {e}")

@app.post("/logs/")
def create_log(log: AttackLog):
    """Insert a new log into the database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO failed_logins (ip_address, timestamp, port, city, region, country, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            log.ip_address,
            log.timestamp,
            log.port,
            log.city,
            log.region,
            log.country,
            log.latitude,
            log.longitude,
        ))

        conn.commit()
        cursor.close()
        conn.close()

        return {"message": "Log added successfully", "log": log}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting log: {e}")
