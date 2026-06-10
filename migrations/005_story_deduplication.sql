ALTER TABLE news_articles
ADD COLUMN IF NOT EXISTS canonical_key VARCHAR(500) NULL,
ADD COLUMN IF NOT EXISTS content_fingerprint VARCHAR(64) NULL,
ADD COLUMN IF NOT EXISTS story_cluster_id VARCHAR(64) NULL,
ADD COLUMN IF NOT EXISTS duplicate_of_article_id INTEGER NULL REFERENCES news_articles(id),
ADD COLUMN IF NOT EXISTS duplicate_reason VARCHAR(50) NULL,
ADD COLUMN IF NOT EXISTS similarity_score FLOAT NULL;

CREATE INDEX IF NOT EXISTS ix_news_articles_content_fingerprint
ON news_articles(content_fingerprint);

CREATE INDEX IF NOT EXISTS ix_news_articles_story_cluster_id
ON news_articles(story_cluster_id);

CREATE INDEX IF NOT EXISTS ix_news_articles_duplicate_of_article_id
ON news_articles(duplicate_of_article_id);

ALTER TABLE news_summaries
ADD COLUMN IF NOT EXISTS story_cluster_id VARCHAR(64) NULL,
ADD COLUMN IF NOT EXISTS source_article_count INTEGER NOT NULL DEFAULT 1;

CREATE INDEX IF NOT EXISTS ix_news_summaries_story_cluster_id
ON news_summaries(story_cluster_id);
