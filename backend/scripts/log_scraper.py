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

# Load environment variables
load_dotenv()

# Database connection parameters
DB_CONFIG = {
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "host": "127.0.0.1",
    "port": 5432,
}

# Updated regex pattern
LOG_PATTERN = r"(\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) .*?Failed password for(?: invalid user)? (\S*) from ([\d.]+) port (\d+)"
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
                        logging.info(f"Matched log entry: timestamp={timestamp}, user={user}, ip={ip_address}, port={port}")
                else:
                    logging.debug(f"Regex failed on line: {line.strip()}")

    except FileNotFoundError:
        logging.error(f"Log file not found: {LOG_FILE}")
    except Exception as e:
        logging.error(f"Error reading log file: {e}")
    
    logging.info(f"Total parsed log entries: {len(parsed_data)}")
    return parsed_data

def insert_into_db(data):
    """Insert data into the database."""
    conn = connect_to_db()
    cursor = conn.cursor()

    for entry in data:
        try:
            sql = """
            INSERT INTO failed_logins (timestamp, ip_address, port)
            VALUES (%s, %s, %s)
            ON CONFLICT (timestamp, ip_address, port) DO NOTHING;
            """
            values = (entry["timestamp"], entry["ip_address"], entry["port"])
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
