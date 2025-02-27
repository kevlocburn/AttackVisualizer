from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import asyncio

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "timescaledb",
    "port": 5432,
}

# Create a connection pool
db_pool = pool.ThreadedConnectionPool(minconn=1, maxconn=10, **DB_CONFIG)

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

# Pydantic Model
class AttackLog(BaseModel):
    ip_address: str
    timestamp: str  # Ensure it's a string
    port: int
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_data(self, data: dict):
        """Send data to all connected clients, removing any that disconnect."""
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"Error sending data: {e}")
                to_remove.append(connection)

        for connection in to_remove:
            self.disconnect(connection)


manager = ConnectionManager()


@app.get("/")
def read_root():
    return {"message": "Welcome to the Server Attack Map API"}


@app.get("/logs/", response_model=List[AttackLog])
def read_logs():
    """Fetch all logs from the database."""
    with db_pool.getconn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
                FROM failed_logins
                ORDER BY timestamp DESC;
            """)
            rows = cursor.fetchall()
    return [
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


@app.get("/charts/top-countries/")
def top_attack_sources(limit: int = 10):
    """Fetch top attack sources by country."""
    with db_pool.getconn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT country, COUNT(*) AS count
                FROM failed_logins
                GROUP BY country
                ORDER BY count DESC
                LIMIT %s;
            """, (limit,))
            rows = cursor.fetchall()
    return [{"country": row[0] or "Unknown", "count": row[1]} for row in rows]


@app.get("/charts/time-of-day/")
def attack_distribution_by_time():
    """Fetch attack distribution by time of day."""
    with db_pool.getconn() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS count
                FROM failed_logins
                GROUP BY hour
                ORDER BY hour;
            """)
            rows = cursor.fetchall()

    hour_data = {int(row[0]): row[1] for row in rows}
    return [{"hour": f"{hour}:00 - {hour + 1}:00", "count": hour_data.get(hour, 0)} for hour in range(24)]


@app.websocket("/ws/maplogs")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to send real-time log data.
    """
    await manager.connect(websocket)
    last_sent_timestamp = None  # Track last sent log time

    try:
        while True:
            try:
                with db_pool.getconn() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT ip_address, timestamp, port, city, region, country, latitude, longitude
                            FROM failed_logins
                            WHERE timestamp > COALESCE(%s, '1970-01-01')
                            ORDER BY timestamp DESC
                            LIMIT 100;
                        """, (last_sent_timestamp,))
                        rows = cursor.fetchall()

                if rows:
                    logs = [
                        {
                            "ip_address": row[0],
                            "timestamp": row[1].strftime("%Y-%m-%d %H:%M:%S"),
                            "port": row[2],
                            "city": row[3],
                            "region": row[4],
                            "country": row[5],
                            "latitude": row[6],
                            "longitude": row[7],
                        }
                        for row in rows
                    ]
                    await manager.send_data({"type": "logs", "data": logs})
                    last_sent_timestamp = logs[0]["timestamp"]

            except Exception as db_error:
                print(f"Database error: {db_error}")

            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {websocket.client}")
        manager.disconnect(websocket)
