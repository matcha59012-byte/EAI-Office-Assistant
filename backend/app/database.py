"""SQLite 数据库连接（SQLAlchemy）。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    """建表（幂等）+ 轻量迁移。"""
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    """增量迁移：旧库补列。"""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    doc_cols = {c["name"] for c in inspector.get_columns("documents")}
    with engine.begin() as conn:
        if "content" not in doc_cols:
            conn.execute(text("ALTER TABLE documents ADD COLUMN content TEXT DEFAULT ''"))
        if "library" not in doc_cols:
            conn.execute(
                text("ALTER TABLE documents ADD COLUMN library VARCHAR(100) DEFAULT '默认资料库'")
            )
    # meetings 表增量列
    try:
        m_cols = {c["name"] for c in inspector.get_columns("meetings")}
        with engine.begin() as conn:
            if "highlights" not in m_cols:
                conn.execute(text("ALTER TABLE meetings ADD COLUMN highlights TEXT DEFAULT ''"))
            if "markdown" not in m_cols:
                conn.execute(text("ALTER TABLE meetings ADD COLUMN markdown TEXT DEFAULT ''"))
    except Exception:  # noqa: BLE001 表可能不存在（还没建）
        pass
    # entities 表增量列
    try:
        e_cols = {c["name"] for c in inspector.get_columns("entities")}
        with engine.begin() as conn:
            if "card_md" not in e_cols:
                conn.execute(text("ALTER TABLE entities ADD COLUMN card_md TEXT DEFAULT ''"))
            if "status" not in e_cols:
                conn.execute(text("ALTER TABLE entities ADD COLUMN status VARCHAR(20) DEFAULT '新'"))
            if "last_contact" not in e_cols:
                conn.execute(text("ALTER TABLE entities ADD COLUMN last_contact VARCHAR(20) DEFAULT ''"))
    except Exception:  # noqa: BLE001
        pass


def get_db():
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
