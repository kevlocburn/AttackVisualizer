import os
import re
import psycopg2
import requests
import time
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(
    filename="log_scraper_debug.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] - %(message)s",
)

# Load environment variables from .env
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "127.0.0.1",
    "port": 5432,
}

# Regex pattern to extract failed login details
LOG_PATTERN = r"(\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) .*?Failed password for(?: invalid user)? (.*?) from ([\d.]+) port (\d+)"
GEO_API_URL = "http://ip-api.com/json/{ip}"
GEO_API_FIELDS = "status,country,regionName,city,lat,lon"
LOG_FILE = "/var/log/auth.log"

def connect_to_db():
    """Establish a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logging.info("Connected to the database successfully.")
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise

def get_last_processed_timestamp():
    """Retrieve the most recent timestamp processed."""
    conn = connect_to_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(timestamp) FROM failed_logins;")
        result = cursor.fetchone()
        return result[0].replace(tzinfo=timezone.utc) if result[0] else None
    except Exception as e:
        logging.error(f"Error fetching last processed timestamp: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def parse_new_logs(last_timestamp):
    """Parse new entries in the log file after the last processed timestamp."""
    parsed_data = []
    try:
        with open(LOG_FILE, "r") as file:
            for line in file:
                logging.debug(f"Processing log line: {line.strip()}")
                match = re.search(LOG_PATTERN, line)
                if match:
                    timestamp_str, user, ip_address, port = match.groups()
                    try:
                        timestamp = datetime.strptime(timestamp_str, "%b %d %H:%M:%S").replace(
                            year=datetime.now().year, tzinfo=timezone.utc
                        )
                    except ValueError as e:
                        logging.warning(f"Timestamp parsing failed: {e} (line: {line.strip()})")
                        continue

                    if not last_timestamp or timestamp > last_timestamp:
                        parsed_data.append({
                            "timestamp": timestamp,
                            "ip_address": ip_address,
                            "port": int(port),
                        })
                else:
                    logging.debug(f"No match found for log line: {line.strip()}")
    except FileNotFoundError:
        logging.error(f"Log file not found: {LOG_FILE}")
    except Exception as e:
        logging.error(f"Error reading log file: {e}")
    
    logging.info(f"Total parsed log entries: {len(parsed_data)}")
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
                logging.warning(f"Rate limited for IP {ip_address}, retrying...")
                time.sleep(2 ** attempt)
            else:
                logging.error(f"Failed API request for IP {ip_address}, Status Code: {response.status_code}")
                break
        except Exception as e:
            logging.error(f"Error resolving geolocation for IP {ip_address}: {e}")
    return {}

def insert_into_db(data):
    """Insert data into the database."""
    conn = connect_to_db()
    cursor = conn.cursor()

    for entry in data:
        try:
            geo_data = resolve_geolocation(entry["ip_address"])
            time.sleep(1)

            sql = """
            INSERT INTO failed_logins (timestamp, ip_address, port, city, region, country, latitude, longitude)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, ip_address, port) DO NOTHING;
            """
            values = (
                entry["timestamp"],
                entry["ip_address"],
                entry["port"],
                geo_data.get("city"),
                geo_data.get("region"),
                geo_data.get("country"),
                geo_data.get("latitude"),
                geo_data.get("longitude"),
            )
            logging.info(f"Executing SQL: {sql} with values {values}")
            cursor.execute(sql, values)

            conn.commit()
            logging.info(f"Inserted entry: {entry}")

        except Exception as e:
            logging.error(f"Error inserting entry {entry}: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    logging.info("Starting log scraper...")

    try:
        last_timestamp = get_last_processed_timestamp()
        new_logs = parse_new_logs(last_timestamp)

        if new_logs:
            insert_into_db(new_logs)
            logging.info(f"Inserted {len(new_logs)} new entries into the database.")
        else:
            logging.info("No new log entries found.")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    logging.info("Log scraper completed.")
