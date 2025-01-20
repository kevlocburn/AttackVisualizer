import os
import re
import psycopg2
import requests
import time
from dotenv import load_dotenv
from datetime import datetime, timezone

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

# Regex pattern to extract failed login details
LOG_PATTERN = r"(\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) .*?Failed password for(?: invalid user)? (.*?) from ([\d.]+) port (\d+)"

# Geolocation API
GEO_API_URL = "http://ip-api.com/json/{ip}"
GEO_API_FIELDS = "status,country,regionName,city,lat,lon"

# File path and check interval
LOG_FILE = "/var/log/auth.log"
CHECK_INTERVAL = 60  # Check every 60 seconds


def parse_new_logs(last_timestamp):
    """Parse new entries in the log file after the last processed timestamp."""
    parsed_data = []
    try:
        with open(LOG_FILE, "r") as file:
            for line in file:
                match = re.search(LOG_PATTERN, line)
                if match:
                    timestamp_str, user, ip_address, port = match.groups()
                    timestamp = datetime.strptime(timestamp_str, "%b %d %H:%M:%S").replace(
                        year=datetime.now().year, tzinfo=timezone.utc
                    )

                    if not last_timestamp or timestamp > last_timestamp:
                        parsed_data.append({
                            "timestamp": timestamp,
                            "ip_address": ip_address,
                            "port": int(port),
                        })
    except FileNotFoundError:
        print(f"Log file not found: {LOG_FILE}")
    return parsed_data


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
                time.sleep(2 ** attempt)
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
            geo_data = resolve_geolocation(entry["ip_address"])
            time.sleep(1)

            cursor.execute(
                """
                INSERT INTO failed_logins (timestamp, ip_address, port, city, region, country, latitude, longitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, ip_address, port) DO NOTHING;
                """,
                (
                    entry["timestamp"],
                    entry["ip_address"],
                    entry["port"],
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
    return result[0].replace(tzinfo=timezone.utc) if result[0] else None


if __name__ == "__main__":
    print("Starting log scraper...")

    try:
        last_timestamp = get_last_processed_timestamp()
        new_logs = parse_new_logs(last_timestamp)
        print(f"Found {len(new_logs)} new log entries.")

        if new_logs:
            insert_into_db(new_logs)
            print(f"Inserted {len(new_logs)} new entries into the database.")

    except Exception as e:
        print(f"Error: {e}")

    print("Log scraper completed.")
