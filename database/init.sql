CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

SELECT pg_reload_conf();

CREATE TABLE IF NOT EXISTS failed_logins (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    port INTEGER NOT NULL,
    city VARCHAR(255),
    region VARCHAR(255),
    country VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    attempts INTEGER DEFAULT 1,
    CONSTRAINT unique_failed_login UNIQUE (timestamp, ip_address, port)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_ip_address ON failed_logins (ip_address);
CREATE INDEX IF NOT EXISTS idx_timestamp ON failed_logins (timestamp);
CREATE INDEX IF NOT EXISTS idx_city_timestamp ON failed_logins (city, timestamp DESC);