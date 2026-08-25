-- Fase 2.2: afirmaciones estructuradas con su evidencia, en vez de solo
-- enlaces sueltos al final del resumen.
CREATE TABLE IF NOT EXISTS story_claims (
    id BIGSERIAL PRIMARY KEY,
    story_id VARCHAR(64) NOT NULL REFERENCES stories(id),
    claim TEXT NOT NULL,
    confidence VARCHAR(20) NOT NULL,
    claim_type VARCHAR(30) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_story_claims_story_id
ON story_claims(story_id);

CREATE TABLE IF NOT EXISTS claim_evidence (
    id BIGSERIAL PRIMARY KEY,
    claim_id BIGINT NOT NULL REFERENCES story_claims(id) ON DELETE CASCADE,
    article_id INTEGER NOT NULL REFERENCES news_articles(id),
    source_excerpt TEXT NULL,
    source_url TEXT NOT NULL,
    published_at TIMESTAMP NULL
);

CREATE INDEX IF NOT EXISTS ix_claim_evidence_claim_id
ON claim_evidence(claim_id);
