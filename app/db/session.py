from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy import text
from sqlalchemy.dialects import sqlite


_engine = None
SCHEMA_VERSION = 1


def init_db(db_url: str) -> None:
    global _engine
    _engine = create_engine(db_url, echo=False)
    SQLModel.metadata.create_all(_engine)
    _ensure_schema(_engine)


def _ensure_schema(engine) -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.connect() as conn:
        _ensure_schema_meta(conn)
        current_version = _get_schema_version(conn)
        applied_changes = False
        for table in SQLModel.metadata.sorted_tables:
            table_name = table.name
            exists = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"),
                {"name": table_name},
            ).fetchone()
            if not exists:
                table.create(conn)
                applied_changes = True
                continue
            existing_cols = {
                row[1] for row in conn.execute(text(f"PRAGMA table_info({table_name})"))
            }
            for column in table.columns:
                if column.name in existing_cols:
                    continue
                col_type = column.type.compile(dialect=sqlite.dialect())
                nullable = "NOT NULL" if not column.nullable else ""
                default = _column_default_for_type(column)
                default_sql = f"DEFAULT {default}" if default is not None else ""
                conn.execute(
                    text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type} {default_sql} {nullable}"
                    )
                )
                applied_changes = True
        if applied_changes and current_version < SCHEMA_VERSION:
            _set_schema_version(conn, SCHEMA_VERSION)
        conn.commit()


def _ensure_schema_meta(conn) -> None:
    exists = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_meta'")
    ).fetchone()
    if not exists:
        conn.execute(
            text("CREATE TABLE schema_meta (version INTEGER NOT NULL)")
        )
        conn.execute(text("INSERT INTO schema_meta (version) VALUES (:version)"), {"version": SCHEMA_VERSION})
    else:
        row = conn.execute(text("SELECT version FROM schema_meta LIMIT 1")).fetchone()
        if not row:
            conn.execute(text("INSERT INTO schema_meta (version) VALUES (:version)"), {"version": SCHEMA_VERSION})


def _get_schema_version(conn) -> int:
    row = conn.execute(text("SELECT version FROM schema_meta LIMIT 1")).fetchone()
    if not row:
        return 0
    return int(row[0])


def _set_schema_version(conn, version: int) -> None:
    conn.execute(text("UPDATE schema_meta SET version = :version"), {"version": version})


def _column_default_for_type(column) -> str | None:
    if column.server_default is not None:
        return str(column.server_default.arg)
    if column.default is not None and column.default.arg is not None:
        value = column.default.arg
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            return str(value)
        return f"'{value}'"
    if column.nullable:
        return None
    col_type = column.type.compile(dialect=sqlite.dialect()).lower()
    if "int" in col_type:
        return "0"
    if "char" in col_type or "text" in col_type:
        return "''"
    if "bool" in col_type:
        return "0"
    return "''"


def get_session() -> Session:
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    return Session(_engine)
