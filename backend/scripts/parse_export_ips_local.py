import os
import psycopg2
import csv
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import time

# Load environment variables from .env
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "localhost",
    "port": 5432,
}

# Geolocation API
GEO_API_URL = "http://ip-api.com/json/{ip}"
GEO_API_FIELDS = "status,country,regionName,city,lat,lon"

def load_failed_logins(file_path, file_format):
    """Load failed login data from CSV or JSON."""
    try:
        if file_format == "csv":
            with open(file_path, "r") as file:
                reader = csv.DictReader(file)
                return [row for row in reader]
        elif file_format == "json":
            with open(file_path, "r") as file:
                return json.load(file)
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return []

def resolve_geolocation(ip_address):
    """Resolve geolocation information for an IP address with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(
                GEO_API_URL.format(ip=ip_address),
                params={"fields": GEO_API_FIELDS},
                timeout=5
            )
            if response.ok:
                data = response.json()
                if data.get("status") == "success":
                    return {
                        "country": data.get("country"),
                        "region": data.get("regionName"),
                        "city": data.get("city"),
                        "latitude": data.get("lat"),
                        "longitude": data.get("lon"),
                    }
            elif response.status_code == 429:
                print(f"Rate limited for IP {ip_address}, retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"Failed API request for IP {ip_address}, Status Code: {response.status_code}")
                break
        except Exception as e:
            print(f"Error resolving geolocation for IP {ip_address}: {e}")
    return {}

def insert_into_db(data):
    """Insert data into the database."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for entry in data:
        try:
            # Parse and ensure timestamp is a datetime object
            timestamp = datetime.strptime(entry["timestamp"], "%b %d %H:%M:%S").replace(year=datetime.now().year)

            geo_data = resolve_geolocation(entry["ip_address"])
            time.sleep(1)  # Increased delay to avoid rate limits

            cursor.execute(
                """
                INSERT INTO failed_logins (timestamp, ip_address, port, city, region, country, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, ip_address, port) DO NOTHING;
                """,
                (
                    timestamp,
                    entry["ip_address"],
                    int(entry["port"]),
                    geo_data.get("city"),
                    geo_data.get("region"),
                    geo_data.get("country"),
                    geo_data.get("latitude"),
                    geo_data.get("longitude"),
                ),
            )
            conn.commit()
            print(f"Inserted entry: {entry}")

        except Exception as e:
            print(f"Error inserting entry {entry}: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

def get_last_processed_timestamp():
    """Retrieve the most recent timestamp processed."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(timestamp) FROM failed_logins;")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    # Return the timestamp as a string
    return result[0] if result[0] else None

if __name__ == "__main__":
    file_format = "csv"
    file_path = "/home/AttackVisualizer/backend/scripts/failed_logins.csv"

    failed_logins = load_failed_logins(file_path, file_format)

    if failed_logins:
        print(f"Loaded {len(failed_logins)} failed login attempts.")
        insert_into_db(failed_logins)
        print("Data successfully inserted into the database.")
    else:
        print("No data loaded. Check the input file.")
