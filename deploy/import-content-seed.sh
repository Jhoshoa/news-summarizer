#!/usr/bin/env bash
set -euo pipefail

# Restores a content-only dump (produced by export-content-seed.sh) into
# THIS server's running postgres container.
#
# Truncates ONLY the same 11 content tables the export script dumps, then
# restores the data, then resets each table's id sequence -- pg_restore
# --data-only inserts rows with explicit ids but never advances the
# SERIAL/IDENTITY sequence, so without this step the app's own next insert
# would collide with a restored id.
#
# subscribers, telegram_link_tokens, analytics_events, summary_refresh_jobs,
# and schema_migrations are never touched -- safe to run against a server
# that already has real subscribers.
#
# Usage (on the server, after copying the dump file here):
#   ./deploy/import-content-seed.sh content_seed.dump

DB_CONTAINER="${DB_CONTAINER:-news-summarizer-new-db}"
DB_USER="${POSTGRES_USER:-news_user}"
DB_NAME="${POSTGRES_DB:-news_summarizer}"
DUMP_FILE="${1:?usage: import-content-seed.sh <path-to-dump-file>}"

if [ ! -f "$DUMP_FILE" ]; then
  echo "No existe el archivo: $DUMP_FILE" >&2
  exit 1
fi

TABLES_SQL="news_categories, news_sources, news_articles, news_summaries, collection_runs, economic_indicator_values, stories, story_articles, story_claims, claim_evidence, story_corrections"

echo "Esto va a TRUNCAR (vaciar) estas tablas en ESTE servidor antes de restaurar:"
echo "  $TABLES_SQL"
echo "subscribers, telegram_link_tokens, analytics_events, summary_refresh_jobs y"
echo "schema_migrations NO se tocan."
read -r -p "Continuar? [y/N] " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "Cancelado."
  exit 1
fi

docker cp "$DUMP_FILE" "$DB_CONTAINER:/tmp/content_seed.dump"

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c \
  "TRUNCATE $TABLES_SQL RESTART IDENTITY CASCADE;"

docker exec "$DB_CONTAINER" pg_restore -U "$DB_USER" -d "$DB_NAME" \
  --data-only /tmp/content_seed.dump

docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT setval(pg_get_serial_sequence('news_categories','id'), COALESCE((SELECT MAX(id) FROM news_categories), 1));
SELECT setval(pg_get_serial_sequence('news_sources','id'), COALESCE((SELECT MAX(id) FROM news_sources), 1));
SELECT setval(pg_get_serial_sequence('news_articles','id'), COALESCE((SELECT MAX(id) FROM news_articles), 1));
SELECT setval(pg_get_serial_sequence('news_summaries','id'), COALESCE((SELECT MAX(id) FROM news_summaries), 1));
SELECT setval(pg_get_serial_sequence('collection_runs','id'), COALESCE((SELECT MAX(id) FROM collection_runs), 1));
SELECT setval(pg_get_serial_sequence('economic_indicator_values','id'), COALESCE((SELECT MAX(id) FROM economic_indicator_values), 1));
-- story_articles has no serial id (its PK is the composite story_id+article_id), so no sequence to reset here.
SELECT setval(pg_get_serial_sequence('story_claims','id'), COALESCE((SELECT MAX(id) FROM story_claims), 1));
SELECT setval(pg_get_serial_sequence('claim_evidence','id'), COALESCE((SELECT MAX(id) FROM claim_evidence), 1));
SELECT setval(pg_get_serial_sequence('story_corrections','id'), COALESCE((SELECT MAX(id) FROM story_corrections), 1));
"

docker exec "$DB_CONTAINER" rm -f /tmp/content_seed.dump

echo
echo "Listo. Conteos actuales:"
docker exec "$DB_CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 'news_articles' AS tabla, count(*) FROM news_articles
UNION ALL SELECT 'news_summaries', count(*) FROM news_summaries
UNION ALL SELECT 'economic_indicator_values', count(*) FROM economic_indicator_values
UNION ALL SELECT 'stories', count(*) FROM stories
UNION ALL SELECT 'subscribers (no tocada)', count(*) FROM subscribers;
"
