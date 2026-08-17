# Database Migrations

SQL migrations in this directory are applied automatically during backend startup.

The application creates missing SQLAlchemy tables first, then applies every `*.sql`
file once, ordered by filename. Applied files are tracked in the database table:

```text
schema_migrations
```

## Rules

- Use a unique numeric prefix: `001_`, `002_`, `003_`, etc.
- Make every migration idempotent when possible.
- Prefer `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, and
  `CREATE INDEX IF NOT EXISTS`.
- Data migrations should guard against duplicate rows with `WHERE NOT EXISTS`.
- Do not edit a migration that has already run in production; add a new migration instead.

## Production

For Dokploy/Hostinger, migrations run as part of backend startup. Before deploying schema
changes, take a database backup from the VPS provider or Postgres volume.

If a migration fails, backend startup logs the failing migration name and the deploy should be
rolled back before retrying.
