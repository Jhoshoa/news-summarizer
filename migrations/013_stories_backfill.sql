-- Backfill de stories/story_articles a partir de articulos que ya tenian
-- story_cluster_id calculado (migracion 005) antes de que existiera la tabla
-- stories. Idempotente: usa ON CONFLICT DO NOTHING, asi que corridas futuras
-- solo insertan lo nuevo que el codigo de la app no haya insertado todavia
-- (por ejemplo si esta migracion corre antes que el primer deploy con el
-- codigo de src/db/repository.py que llena stories en cada insercion).

INSERT INTO stories (
    id,
    canonical_title,
    category,
    country,
    first_published_at,
    last_updated_at,
    current_status,
    article_count,
    source_count
)
SELECT
    a.story_cluster_id,
    (ARRAY_AGG(a.title ORDER BY a.published_at ASC))[1],
    (ARRAY_AGG(c.name ORDER BY a.published_at ASC))[1],
    COALESCE((ARRAY_AGG(a.country ORDER BY a.published_at ASC))[1], 'BO'),
    MIN(a.published_at),
    MAX(a.published_at),
    'developing',
    COUNT(*)::int,
    COUNT(DISTINCT a.source_id)::int
FROM news_articles a
JOIN news_categories c ON c.id = a.category_id
WHERE a.story_cluster_id IS NOT NULL
GROUP BY a.story_cluster_id
ON CONFLICT (id) DO NOTHING;

INSERT INTO story_articles (story_id, article_id, similarity_score, relationship_type)
SELECT
    a.story_cluster_id,
    a.id,
    a.similarity_score,
    CASE WHEN a.duplicate_of_article_id IS NOT NULL THEN 'duplicate' ELSE 'original_report' END
FROM news_articles a
WHERE a.story_cluster_id IS NOT NULL
ON CONFLICT (story_id, article_id) DO NOTHING;
