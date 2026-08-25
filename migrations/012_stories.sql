CREATE TABLE IF NOT EXISTS stories (
    id VARCHAR(64) PRIMARY KEY,
    canonical_title VARCHAR(300) NOT NULL,
    short_summary TEXT NULL,
    detailed_summary TEXT NULL,
    category VARCHAR(60) NULL,
    country VARCHAR(10) NOT NULL DEFAULT 'BO',
    department VARCHAR(80) NULL,
    city VARCHAR(80) NULL,
    importance_score FLOAT NULL,
    confidence_score FLOAT NULL,
    first_published_at TIMESTAMP NOT NULL,
    last_updated_at TIMESTAMP NOT NULL,
    current_status VARCHAR(40) NOT NULL DEFAULT 'developing',
    article_count INTEGER NOT NULL DEFAULT 1,
    source_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS ix_stories_category
ON stories(category);

CREATE INDEX IF NOT EXISTS ix_stories_last_updated_at
ON stories(last_updated_at);

CREATE TABLE IF NOT EXISTS story_articles (
    story_id VARCHAR(64) NOT NULL REFERENCES stories(id),
    article_id INTEGER NOT NULL REFERENCES news_articles(id),
    similarity_score FLOAT NULL,
    relationship_type VARCHAR(30) NOT NULL DEFAULT 'original_report',
    PRIMARY KEY (story_id, article_id)
);

CREATE INDEX IF NOT EXISTS ix_story_articles_article_id
ON story_articles(article_id);
