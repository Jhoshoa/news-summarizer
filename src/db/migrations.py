from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


@dataclass(frozen=True)
class Migration:
    version: str
    path: Path
    sql: str


SCHEMA_MIGRATIONS_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""
MIGRATION_LOCK_SQL = "SELECT pg_advisory_xact_lock(hashtext('news_summarizer_schema_migrations'))"


async def apply_sql_migrations(
    engine: AsyncEngine,
    migrations_path: Path | None = None,
) -> list[str]:
    """Apply SQL migrations once, tracked by filename stem."""

    migrations = load_migrations(migrations_path or default_migrations_path())
    if not migrations:
        return []

    applied_versions: list[str] = []
    async with engine.begin() as conn:
        await conn.exec_driver_sql(MIGRATION_LOCK_SQL)
        await conn.execute(text(SCHEMA_MIGRATIONS_SQL))
        already_applied = await get_applied_versions(conn)

        for migration in migrations:
            if migration.version in already_applied:
                continue

            logger.info(f"Aplicando migracion DB: {migration.path.name}")
            for statement in split_sql_statements(migration.sql):
                await conn.exec_driver_sql(statement)

            await conn.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": migration.version},
            )
            applied_versions.append(migration.version)

    if applied_versions:
        logger.info(f"Migraciones DB aplicadas: {', '.join(applied_versions)}")

    return applied_versions


def default_migrations_path() -> Path:
    return Path(__file__).resolve().parents[2] / "migrations"


def load_migrations(migrations_path: Path) -> list[Migration]:
    if not migrations_path.exists():
        logger.warning(f"Directorio de migraciones no encontrado: {migrations_path}")
        return []

    return [
        Migration(
            version=path.stem,
            path=path,
            sql=path.read_text(encoding="utf-8"),
        )
        for path in sorted(migrations_path.glob("*.sql"))
    ]


async def get_applied_versions(conn: AsyncConnection) -> set[str]:
    result = await conn.execute(text("SELECT version FROM schema_migrations"))
    return {str(row[0]) for row in result}


def split_sql_statements(sql: str) -> list[str]:
    statements = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    index = 0

    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            index += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                index += 2
                continue
            index += 1
            continue

        if not in_single_quote and not in_double_quote:
            if char == "-" and next_char == "-":
                current.extend([char, next_char])
                in_line_comment = True
                index += 2
                continue
            if char == "/" and next_char == "*":
                current.extend([char, next_char])
                in_block_comment = True
                index += 2
                continue

        if char == "'" and not in_double_quote:
            current.append(char)
            if in_single_quote and next_char == "'":
                current.append(next_char)
                index += 2
                continue
            in_single_quote = not in_single_quote
            index += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current.append(char)
            index += 1
            continue

        if char == ";" and not in_single_quote and not in_double_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            index += 1
            continue

        current.append(char)
        index += 1

    statement = "".join(current).strip()
    if statement:
        statements.append(statement)

    return statements


def migration_versions(migrations: Iterable[Migration]) -> list[str]:
    return [migration.version for migration in migrations]
