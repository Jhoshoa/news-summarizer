CREATE TABLE IF NOT EXISTS economic_indicator_values (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    indicator_code VARCHAR(160) NOT NULL,
    indicator_name VARCHAR(250) NOT NULL,
    indicator_group VARCHAR(250) NOT NULL,
    value NUMERIC(18, 6) NOT NULL,
    unit VARCHAR(80),
    currency VARCHAR(20),
    asset VARCHAR(20),
    side VARCHAR(20),
    observed_at DATE,
    collected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    snapshot_key VARCHAR(64) NOT NULL,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_source
    ON economic_indicator_values (source);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_indicator_code
    ON economic_indicator_values (indicator_code);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_indicator_group
    ON economic_indicator_values (indicator_group);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_side
    ON economic_indicator_values (side);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_observed_at
    ON economic_indicator_values (observed_at);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_collected_at
    ON economic_indicator_values (collected_at);

CREATE INDEX IF NOT EXISTS ix_economic_indicator_values_snapshot_key
    ON economic_indicator_values (snapshot_key);
