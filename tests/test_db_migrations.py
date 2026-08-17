from pathlib import Path

from src.db.migrations import load_migrations, migration_versions, split_sql_statements


def test_load_migrations_orders_sql_files_by_filename(tmp_path: Path):
    (tmp_path / "002_second.sql").write_text("SELECT 2;", encoding="utf-8")
    (tmp_path / "001_first.sql").write_text("SELECT 1;", encoding="utf-8")

    migrations = load_migrations(tmp_path)

    assert migration_versions(migrations) == ["001_first", "002_second"]


def test_split_sql_statements_keeps_semicolon_inside_string_literal():
    sql = """
    INSERT INTO example (value) VALUES ('texto; con punto y coma');
    -- comentario con ;
    SELECT 1;
    """

    statements = split_sql_statements(sql)

    assert statements == [
        "INSERT INTO example (value) VALUES ('texto; con punto y coma')",
        "-- comentario con ;\n    SELECT 1",
    ]


def test_migration_numeric_prefixes_are_unique():
    migration_dir = Path(__file__).resolve().parents[1] / "migrations"
    prefixes = [path.name.split("_", 1)[0] for path in migration_dir.glob("*.sql")]

    assert len(prefixes) == len(set(prefixes))
