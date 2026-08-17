CREATE TABLE IF NOT EXISTS summary_refresh_jobs (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    time_of_day VARCHAR(20) NOT NULL DEFAULT 'manual',
    refresh BOOLEAN NOT NULL DEFAULT FALSE,
    requested_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP NULL,
    finished_at TIMESTAMP NULL,
    result JSONB NULL,
    error_message TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_summary_refresh_jobs_status
ON summary_refresh_jobs(status);

CREATE INDEX IF NOT EXISTS ix_summary_refresh_jobs_requested_at
ON summary_refresh_jobs(requested_at);
