import os
import re
import psycopg2
import requests
import time
from dotenv import load_dotenv
from datetime import datetime, timezone
import logging

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "timescaledb",
    "port": 5432,
}

# Log file location
LOG_FILE = "/host_var_log/auth.log"

# Regex pattern for failed SSH logins
LOG_PATTERN = re.compile(
    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}) .*? (?:Invalid user|Failed password for(?: invalid user)?) (\S+) from ([\d.]+) port (\d+)"
)

# Geolocation API
GEO_API_URL = "http://ip-api.com/json/{ip}"
GEO_API_FIELDS = "status,country,regionName,city,lat,lon"

# Cache for IP lookups (avoid duplicate API calls)
ip_cache = {}

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# File to store last processed line
LAST_LINE_FILE = "/tmp/last_line_processed.txt"

def get_last_processed_line():
    """Retrieve the last processed line number."""
    try:
        with open(LAST_LINE_FILE, "r") as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return 0

def set_last_processed_line(line_number):
    """Store the last processed line number."""
    with open(LAST_LINE_FILE, "w") as f:
        f.write(str(line_number))

def parse_new_logs():
    """Parse new log lines and return failed login attempts."""
    parsed_data = []
    last_line_number = get_last_processed_line()

    try:
        with open(LOG_FILE, "r") as file:
            lines = file.readlines()
            for i, line in enumerate(lines):
                if i < last_line_number:
                    continue  # Skip already processed lines

                match = LOG_PATTERN.search(line)
                if match:
                    timestamp_str, user, ip_address, port = match.groups()
                    timestamp = datetime.strptime(timestamp_str, "%b %d %H:%M:%S").replace(
                        year=datetime.now().year, tzinfo=timezone.utc
                    )
                    
                    # Cache the IP lookup
                    geo_data = ip_cache.get(ip_address) or resolve_geolocation(ip_address)
                    ip_cache[ip_address] = geo_data

                    entry = {
                        "timestamp": timestamp,
                        "ip_address": ip_address,
                        "port": int(port),
                        "city": geo_data.get("city"),
                        "region": geo_data.get("region"),
                        "country": geo_data.get("country"),
                        "latitude": geo_data.get("latitude"),
                        "longitude": geo_data.get("longitude"),
                    }
                    parsed_data.append(entry)

            set_last_processed_line(len(lines))  # Store the last processed line
    except FileNotFoundError:
        logging.error(f"Log file not found: {LOG_FILE}")

    return parsed_data

def resolve_geolocation(ip_address):
    """Resolve geolocation information for an IP address with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(GEO_API_URL.format(ip=ip_address), params={"fields": GEO_API_FIELDS}, timeout=5)
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
                logging.warning(f"Rate limited for IP {ip_address}, retrying...")
                time.sleep(2 ** attempt)
            else:
                logging.error(f"Failed API request for IP {ip_address}, Status Code: {response.status_code}")
                break
        except Exception as e:
            logging.error(f"Error resolving geolocation for IP {ip_address}: {e}")
    return {}

def insert_into_db(data):
    """Batch insert data into the database."""
    if not data:
        return

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.executemany(
            """
            INSERT INTO failed_logins (timestamp, ip_address, port, city, region, country, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, ip_address, port) DO NOTHING;
            """,
            [(entry["timestamp"], entry["ip_address"], entry["port"], entry["city"], entry["region"], entry["country"], entry["latitude"], entry["longitude"]) for entry in data]
        )
        conn.commit()
        logging.info(f"Inserted {len(data)} new log entries into the database.")
    except Exception as e:
        logging.error(f"Database insertion error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    logging.info("Starting log scraper...")

    try:
        new_logs = parse_new_logs()
        logging.info(f"Found {len(new_logs)} new log entries.")

        if new_logs:
            insert_into_db(new_logs)

    except Exception as e:
        logging.error(f"Error: {e}")

    logging.info("Log scraper completed.")
