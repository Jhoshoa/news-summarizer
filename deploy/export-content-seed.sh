#!/usr/bin/env bash
set -euo pipefail

# Git Bash on Windows rewrites any argument that looks like a Unix path
# (e.g. "/tmp/content_seed.dump") into a Windows path before handing it to
# docker.exe -- fatal here, since that path must stay literal, it's inside
# the Linux container, not on the Windows host. Harmless no-op on Linux/macOS.
export MSYS_NO_PATHCONV=1

# Dumps ONLY the content tables (categories, sources, articles, summaries,
# story clustering, economic indicators) from a running local DB container.
#
# Deliberately excludes subscribers, telegram_link_tokens, analytics_events,
# summary_refresh_jobs, and schema_migrations -- this script is meant to seed
# a fresh(er) production database with real collected content without ever
# touching real subscriber/telegram data or job/schema bookkeeping state that
# belongs to each environment independently.
#
# Usage (from the repo root, with the local stack running):
#   ./deploy/export-content-seed.sh [output-file]
#
# Produces a custom-format pg_dump file (portable, works with any matching
# postgres major version -- this project pins postgres:15-alpine everywhere,
# local and production, via the same docker-compose.yml).

DB_CONTAINER="${DB_CONTAINER:-news-summarizer-new-db}"
DB_USER="${POSTGRES_USER:-news_user}"
DB_NAME="${POSTGRES_DB:-news_summarizer}"
OUT_FILE="${1:-content_seed.dump}"

# Keep this list in sync with import-content-seed.sh's TRUNCATE list --
# both scripts must agree on exactly which tables are "content".
TABLES=(
  news_categories
  news_sources
  news_articles
  news_summaries
  collection_runs
  economic_indicator_values
  stories
  story_articles
  story_claims
  claim_evidence
  story_corrections
)

TABLE_ARGS=()
for t in "${TABLES[@]}"; do
  TABLE_ARGS+=(-t "$t")
done

echo "Dumping ${#TABLES[@]} content tables from $DB_CONTAINER ($DB_NAME)..."
docker exec "$DB_CONTAINER" pg_dump -U "$DB_USER" -d "$DB_NAME" \
  --data-only --format=custom "${TABLE_ARGS[@]}" \
  -f /tmp/content_seed.dump

docker cp "$DB_CONTAINER:/tmp/content_seed.dump" "$OUT_FILE"
docker exec "$DB_CONTAINER" rm -f /tmp/content_seed.dump

echo "Wrote $OUT_FILE ($(du -h "$OUT_FILE" | cut -f1))"
echo
echo "Next steps:"
echo "  1. scp -i path/to/key.pem $OUT_FILE user@<server>:~/"
echo "  2. On the server: ./deploy/import-content-seed.sh $OUT_FILE"
