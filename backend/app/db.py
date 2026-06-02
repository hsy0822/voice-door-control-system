"""数据库引擎与会话。"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base, User

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{settings.db_path.as_posix()}"
        _engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
        Base.metadata.create_all(bind=_engine)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_db() -> Generator[Session, None, None]:
    get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_admin_user() -> None:
    """首次启动时创建默认管理员账号。"""
    from app.security import hash_password

    get_engine()
    db = _SessionLocal()
    try:
        exists = db.scalar(
            select(User.id).where(User.username == settings.seed_admin_username)
        )
        if exists:
            return
        db.add(
            User(
                username=settings.seed_admin_username,
                password_hash=hash_password(settings.seed_admin_password),
                role="admin",
                status="active",
                door_enabled=True,
            )
        )
        db.commit()
    finally:
        db.close()
