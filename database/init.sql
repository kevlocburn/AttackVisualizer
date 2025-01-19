CREATE TABLE attacks (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    source_ip VARCHAR(45) NOT NULL,
    attack_type VARCHAR(50) NOT NULL,
    details TEXT,
    location GEOGRAPHY(POINT, 4326)
);

CREATE INDEX idx_attacks_timestamp ON attacks (timestamp);
CREATE INDEX idx_attacks_source_ip ON attacks (source_ip);