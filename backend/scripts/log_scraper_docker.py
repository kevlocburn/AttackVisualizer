import os
import re
import psycopg2
import requests
import time
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone

# Setup logging
LOG_FILE_PATH = "/var/log/log_scraper_docker.log"
logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
console_handler.setFormatter(formatter)
logging.getLogger().addHandler(console_handler)

logging.info("Starting log scraper...")

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
LOG_PATTERN = r"(\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) .*?Failed password for(?: invalid user)? (\S+) from ([\d.]+) port (\d+)"

# Geolocation API
GEO_API_URL = "http://ip-api.com/json/{ip}"
GEO_API_FIELDS = "status,country,regionName,city,lat,lon"

# File path and check interval
LOG_FILE = "/host_var_log/auth.log"
CHECK_INTERVAL = 60  # Check every 60 seconds

def test_db_connection():
    """Test database connection to ensure it works before proceeding."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.close()
        logging.info("Database connection successful.")
    except Exception as e:
        logging.error(f"Database connection failed: {e}")

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
                    timestamp = datetime.strptime(timestamp_str, "%b %d %H:%M:%S").replace(
                        year=datetime.now().year, tzinfo=timezone.utc
                    )

                    if not last_timestamp or timestamp > last_timestamp:
                        entry = {
                            "timestamp": timestamp,
                            "ip_address": ip_address,
                            "port": int(port),
                            "user": user,
                        }
                        logging.info(f"Extracted log entry: {entry}")
                        parsed_data.append(entry)
                else:
                    logging.debug(f"No match found for log line: {line.strip()}")
    except FileNotFoundError:
        logging.error(f"Log file not found: {LOG_FILE}")
    except Exception as e:
        logging.error(f"Error parsing logs: {e}")

    return parsed_data

def resolve_geolocation(ip_address):
    """Resolve geolocation information for an IP address with retries."""
    retries = 3
    for attempt in range(retries):
        try:
            logging.info(f"Resolving geolocation for IP: {ip_address}")
            response = requests.get(
                GEO_API_URL.format(ip=ip_address),
                params={"fields": GEO_API_FIELDS},
                timeout=5
            )
            if response.ok:
                data = response.json()
                if data.get("status") == "success":
                    logging.info(f"Geolocation data: {data}")
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
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        logging.info("Connected to the database for insertion.")

        for entry in data:
            try:
                geo_data = resolve_geolocation(entry["ip_address"])
                time.sleep(1)  # Prevent rate limiting

                cursor.execute(
                    """
                    INSERT INTO failed_logins (timestamp, ip_address, port, city, region, country, latitude, longitude, user)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        entry["user"],
                    ),
                )
                conn.commit()
                logging.info(f"Inserted entry: {entry}")

            except Exception as e:
                logging.error(f"Error inserting entry {entry}: {e}")
                conn.rollback()

        cursor.close()
        conn.close()
        logging.info("Database connection closed after insertion.")
    except Exception as e:
        logging.error(f"Database connection failed during insertion: {e}")

def get_last_processed_timestamp():
    """Retrieve the most recent timestamp processed."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM failed_logins;")
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and result[0]:
            logging.info(f"Last processed timestamp: {result[0]}")
            return result[0].replace(tzinfo=timezone.utc)
        else:
            logging.info("No previous logs found in the database.")
            return None
    except Exception as e:
        logging.error(f"Error fetching last timestamp: {e}")
        return None

if __name__ == "__main__":
    logging.info("Log scraper started.")

    try:
        test_db_connection()
        last_timestamp = get_last_processed_timestamp()
        new_logs = parse_new_logs(last_timestamp)

        logging.info(f"Found {len(new_logs)} new log entries.")

        if new_logs:
            insert_into_db(new_logs)
            logging.info(f"Inserted {len(new_logs)} new entries into the database.")

    except Exception as e:
        logging.error(f"Unexpected error: {e}")

    logging.info("Log scraper completed.")
