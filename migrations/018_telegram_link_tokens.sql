CREATE TABLE IF NOT EXISTS telegram_link_tokens (
    token VARCHAR(64) PRIMARY KEY,
    categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    frequency VARCHAR(20) NOT NULL DEFAULT 'diario',
    preferred_hour SMALLINT NOT NULL DEFAULT 9,
    timezone VARCHAR(50) NOT NULL DEFAULT 'America/La_Paz',
    consent_accepted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS ix_telegram_link_tokens_expires_at
    ON telegram_link_tokens (expires_at);
