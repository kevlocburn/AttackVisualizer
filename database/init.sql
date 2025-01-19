CREATE TABLE failed_logins (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    port INTEGER NOT NULL,
    city VARCHAR(255),
    region VARCHAR(255),
    country VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    attempts INTEGER DEFAULT 1
);

CREATE INDEX idx_ip_address ON failed_logins (ip_address);
CREATE INDEX idx_timestamp ON failed_logins (timestamp);
