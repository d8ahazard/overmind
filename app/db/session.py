from sqlmodel import Session, SQLModel, create_engine

_engine = None


def init_db(db_url: str) -> None:
    global _engine
    _engine = create_engine(db_url, echo=False)
    SQLModel.metadata.create_all(_engine)


def get_session() -> Session:
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db first.")
    return Session(_engine)
