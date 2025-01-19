import os
import re
import psycopg2
import requests
import time
from dotenv import load_dotenv

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

    with open(LOG_FILE, "r") as file:
        for line in file:
            match = re.search(LOG_PATTERN, line)
            if match:
                timestamp, user, ip_address, port = match.groups()
                if timestamp > last_timestamp:  # Only process new entries
                    parsed_data.append({
                        "timestamp": timestamp,
                        "ip_address": ip_address,
                        "port": int(port),
                    })

    return parsed_data

def resolve_geolocation(ip_address):
    """Resolve geolocation information for an IP address."""
    try:
        response = requests.get(GEO_API_URL.format(ip=ip_address), params={"fields": GEO_API_FIELDS}, timeout=5)
        data = response.json()
        if data.get("status") == "success":
            return {
                "country": data.get("country"),
                "region": data.get("regionName"),
                "city": data.get("city"),
                "latitude": data.get("lat"),
                "longitude": data.get("lon"),
            }
    except requests.RequestException as e:
        print(f"Error fetching geolocation for IP {ip_address}: {e}")
    return {}

def insert_into_db(data):
    """Insert parsed data into the database."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for entry in data:
        try:
            geo_data = resolve_geolocation(entry["ip_address"])
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
        except Exception as e:
            print(f"Error inserting entry {entry}: {e}")

    conn.commit()
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
    return result[0] if result[0] else ""

if __name__ == "__main__":
    print("Starting log scraper...")

    while True:
        try:
            last_timestamp = get_last_processed_timestamp()
            new_logs = parse_new_logs(last_timestamp)
            print(f"Found {len(new_logs)} new log entries.")

            if new_logs:
                insert_into_db(new_logs)
                print(f"Inserted {len(new_logs)} new entries into the database.")

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(CHECK_INTERVAL)
