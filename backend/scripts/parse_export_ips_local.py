import os
import re
import psycopg2
import csv
import json
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

# File paths
LOG_FILE = r"C:\logs\auth.log"  # Raw string for Windows paths
EXPORT_CSV = "failed_logins.csv"
EXPORT_JSON = "failed_logins.json"

def parse_logs():
    """Parse /var/log/auth.log and extract failed login attempts."""
    parsed_data = []

    with open(LOG_FILE, "r") as file:
        for line in file:
            match = re.search(LOG_PATTERN, line)
            if match:
                timestamp, user, ip_address, port = match.groups()
                parsed_data.append({
                    "timestamp": timestamp,
                    "ip_address": ip_address,
                    "port": int(port),
                })

    return parsed_data

def insert_into_db(data):
    """Insert parsed data into the database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for entry in data:
            cursor.execute(
                """
                INSERT INTO failed_logins (timestamp, ip_address, port)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING;
                """,
                (entry["timestamp"], entry["ip_address"], entry["port"]),
            )

        conn.commit()
    except Exception as e:
        print(f"Error inserting data into database: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

def export_to_csv(data):
    """Export parsed data to a CSV file."""
    with open(EXPORT_CSV, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["timestamp", "ip_address", "port"])
        writer.writeheader()
        writer.writerows(data)

def export_to_json(data):
    """Export parsed data to a JSON file."""
    with open(EXPORT_JSON, "w") as jsonfile:
        json.dump(data, jsonfile, indent=4)

if __name__ == "__main__":
    # Step 1: Parse logs
    parsed_data = parse_logs()
    print(f"Parsed {len(parsed_data)} failed login attempts.")

    # Step 2: Insert into database
    insert_into_db(parsed_data)
    print("Inserted data into the database.")

    # Step 3: Export data
    export_to_csv(parsed_data)
    print(f"Data exported to {EXPORT_CSV}.")
    export_to_json(parsed_data)
    print(f"Data exported to {EXPORT_JSON}.")
