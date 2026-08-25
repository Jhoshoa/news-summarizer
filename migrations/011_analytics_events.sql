CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    event_name VARCHAR(60) NOT NULL,
    user_id INTEGER NULL REFERENCES subscribers(id),
    session_id VARCHAR(80) NULL,
    country VARCHAR(10) NULL,
    department VARCHAR(80) NULL,
    category VARCHAR(60) NULL,
    story_id VARCHAR(64) NULL,
    source_id VARCHAR(120) NULL,
    device VARCHAR(20) NULL,
    metadata_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_analytics_events_event_name
ON analytics_events(event_name);

CREATE INDEX IF NOT EXISTS ix_analytics_events_user_id
ON analytics_events(user_id);

CREATE INDEX IF NOT EXISTS ix_analytics_events_session_id
ON analytics_events(session_id);

CREATE INDEX IF NOT EXISTS ix_analytics_events_story_id
ON analytics_events(story_id);

CREATE INDEX IF NOT EXISTS ix_analytics_events_created_at
ON analytics_events(created_at);
