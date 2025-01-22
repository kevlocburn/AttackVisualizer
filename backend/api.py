from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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
    allow_origins=["http://localhost:3000", "https://hack.kevinlockburner.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model
class AttackLog(BaseModel):
    ip_address: str
    timestamp: str  # Ensure this is a string
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


@app.get("/charts/top-countries/")
def top_attack_sources(limit: int = 10):
    """Fetch top attack sources by country."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT country, COUNT(*) AS count
            FROM failed_logins
            GROUP BY country
            ORDER BY count DESC
            LIMIT %s;
        """, (limit,))
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return [{"country": row[0] or "Unknown", "count": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top attack sources: {e}")


@app.get("/charts/attack-trends/")
def attack_trends():
    """Fetch attack trends over time."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT DATE(timestamp) AS attack_date, COUNT(*) AS count
            FROM failed_logins
            GROUP BY attack_date
            ORDER BY attack_date;
        """)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        return [{"date": str(row[0]), "count": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attack trends: {e}")


@app.get("/charts/time-of-day/")
def attack_distribution_by_time():
    """Fetch attack distribution by time of day."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS count
            FROM failed_logins
            GROUP BY hour
            ORDER BY hour;
        """)
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        # Fill missing hours with 0 counts
        hour_data = {int(row[0]): row[1] for row in rows}
        return [{"hour": f"{hour}:00 - {hour + 1}:00", "count": hour_data.get(hour, 0)} for hour in range(24)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching time of day distribution: {e}")


@app.get("/logs/count/")
def get_log_count():
    """Get the total number of log entries."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM failed_logins;")
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching log count: {e}")
