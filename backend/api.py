from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import asyncio

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

# Create a connection pool (adjust minconn and maxconn as needed)
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
        to_remove = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                print(f"Error sending data to client: {e}")
                to_remove.append(connection)
        # Remove disconnected clients
        for connection in to_remove:
            self.disconnect(connection)

manager = ConnectionManager()

@app.get("/")
def read_root():
    """Root endpoint."""
    return {"message": "Welcome to the Server Attack Map API"}

@app.get("/logs/", response_model=List[AttackLog])
def read_logs():
    """Fetch all logs from the database."""
    conn = db_pool.getconn()
    try:
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
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching logs: {e}")
    finally:
        db_pool.putconn(conn)

@app.get("/maplogs/", response_model=List[AttackLog])
def read_map_logs():
    """Fetch last 100 logs with max 2 repeating cities."""
    conn = db_pool.getconn()
    try:
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
        return maplogs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching map logs: {e}")
    finally:
        db_pool.putconn(conn)

@app.get("/charts/top-countries/")
def top_attack_sources(limit: int = 10):
    """Fetch top attack sources by country."""
    conn = db_pool.getconn()
    try:
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
        return [{"country": row[0] or "Unknown", "count": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching top attack sources: {e}")
    finally:
        db_pool.putconn(conn)

@app.get("/charts/attack-trends/")
def attack_trends():
    """Fetch attack trends over time."""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DATE(timestamp) AS attack_date, COUNT(*) AS count
            FROM failed_logins
            GROUP BY attack_date
            ORDER BY attack_date;
        """)
        rows = cursor.fetchall()
        cursor.close()
        return [{"date": str(row[0]), "count": row[1]} for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching attack trends: {e}")
    finally:
        db_pool.putconn(conn)

@app.get("/charts/time-of-day/")
def attack_distribution_by_time():
    """Fetch attack distribution by time of day."""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT EXTRACT(HOUR FROM timestamp) AS hour, COUNT(*) AS count
            FROM failed_logins
            GROUP BY hour
            ORDER BY hour;
        """)
        rows = cursor.fetchall()
        cursor.close()
        # Fill missing hours with 0 counts
        hour_data = {int(row[0]): row[1] for row in rows}
        return [{"hour": f"{hour}:00 - {hour + 1}:00", "count": hour_data.get(hour, 0)} for hour in range(24)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching time of day distribution: {e}")
    finally:
        db_pool.putconn(conn)

@app.get("/logs/count/")
def get_log_count():
    """Get the total number of log entries."""
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM failed_logins;")
        count = cursor.fetchone()[0]
        cursor.close()
        return {"count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching log count: {e}")
    finally:
        db_pool.putconn(conn)

@app.post("/logs/")
def create_log(log: AttackLog):
    """Insert a new log into the database."""
    conn = db_pool.getconn()
    try:
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
        return {"message": "Log added successfully", "log": log}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inserting log: {e}")
    finally:
        db_pool.putconn(conn)

@app.websocket("/ws/maplogs")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint to send real-time log data.
    """
    await manager.connect(websocket)
    last_sent_timestamp = None  # Track the timestamp of the last sent log

    try:
        while True:
            try:
                conn = db_pool.getconn()
                try:
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
                    cursor.close()
                finally:
                    db_pool.putconn(conn)

                # Send only new logs based on timestamp
                if logs and (last_sent_timestamp is None or logs[0]["timestamp"] > last_sent_timestamp):
                    await manager.send_data({"type": "logs", "data": logs})
                    last_sent_timestamp = logs[0]["timestamp"]

            except Exception as db_error:
                print(f"Database error: {db_error}")

            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        print(f"WebSocket disconnected: {websocket.client}")
        manager.disconnect(websocket)
