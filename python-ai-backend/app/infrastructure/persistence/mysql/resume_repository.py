# author: jf
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote, urlsplit
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, MetaData, String, Table, URL, create_engine, delete, func, select, update
from sqlalchemy.engine import Connection, Engine, RowMapping

from app.application.ports.resume_repository import (
    LastResumeDeletionError,
    ResumeNotFoundError,
    ResumeRepository,
    StoredResume,
)


@dataclass(frozen=True, slots=True)
class MySqlConnectionConfig:
    host: str
    port: int
    database: str
    username: str
    password: str


_METADATA = MetaData()
_AUTH_USERS = Table(
    "auth_users",
    _METADATA,
    Column("user_id", String(64), primary_key=True),
)
_USER_RESUMES = Table(
    "user_resumes",
    _METADATA,
    Column("resume_id", String(64), primary_key=True),
    Column("user_id", String(64), nullable=False),
    Column("resume_name", String(80), nullable=False),
    Column("resume_data_json", JSON, nullable=False),
    Column("is_active", Boolean, nullable=False),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)


class MySqlResumeRepository(ResumeRepository):
    def __init__(self, datasource_url: str, username: str = "", password: str = "") -> None:
        config = _parse_mysql_config(datasource_url, username, password)
        self._engine = _build_engine(config)

    def list_by_user(self, user_id: str) -> list[StoredResume]:
        statement = (
            select(_USER_RESUMES)
            .where(_USER_RESUMES.c.user_id == user_id)
            .order_by(
                _USER_RESUMES.c.is_active.desc(),
                _USER_RESUMES.c.updated_at.desc(),
                _USER_RESUMES.c.created_at.desc(),
            )
        )
        with self._engine.connect() as connection:
            return [_to_stored_resume(row) for row in connection.execute(statement).mappings().all()]

    def get_owned(self, user_id: str, resume_id: str) -> StoredResume | None:
        with self._engine.connect() as connection:
            row = self._select_owned(connection, user_id, resume_id)
            return _to_stored_resume(row) if row else None

    def create(self, user_id: str, name: str, data: dict[str, Any]) -> StoredResume:
        # 首份简历判断与写入放在同一事务中，并锁定用户行来串行化同账号并发创建。
        resume_id = str(uuid4())
        with self._engine.begin() as connection:
            self._lock_user(connection, user_id)
            total = connection.scalar(
                select(func.count()).select_from(_USER_RESUMES).where(_USER_RESUMES.c.user_id == user_id)
            )
            connection.execute(
                _USER_RESUMES.insert().values(
                    resume_id=resume_id,
                    user_id=user_id,
                    resume_name=name,
                    resume_data_json=data,
                    is_active=int(total or 0) == 0,
                )
            )
            row = self._select_owned(connection, user_id, resume_id)
        if row is None:
            raise ResumeNotFoundError("简历不存在")
        return _to_stored_resume(row)

    def update(self, user_id: str, resume_id: str, name: str, data: dict[str, Any]) -> StoredResume:
        statement = (
            update(_USER_RESUMES)
            .where(
                _USER_RESUMES.c.user_id == user_id,
                _USER_RESUMES.c.resume_id == resume_id,
            )
            .values(
                resume_name=name,
                resume_data_json=data,
                updated_at=func.current_timestamp(),
            )
        )
        with self._engine.begin() as connection:
            result = connection.execute(statement)
            row = self._select_owned(connection, user_id, resume_id)
            if result.rowcount == 0 and row is None:
                raise ResumeNotFoundError("简历不存在")
        if row is None:
            raise ResumeNotFoundError("简历不存在")
        return _to_stored_resume(row)

    def activate(self, user_id: str, resume_id: str) -> StoredResume:
        with self._engine.begin() as connection:
            self._lock_user(connection, user_id)
            if self._select_owned(connection, user_id, resume_id) is None:
                raise ResumeNotFoundError("简历不存在")
            connection.execute(
                update(_USER_RESUMES)
                .where(
                    _USER_RESUMES.c.user_id == user_id,
                    _USER_RESUMES.c.is_active.is_(True),
                )
                .values(is_active=False)
            )
            connection.execute(
                update(_USER_RESUMES)
                .where(
                    _USER_RESUMES.c.user_id == user_id,
                    _USER_RESUMES.c.resume_id == resume_id,
                )
                .values(is_active=True, updated_at=func.current_timestamp())
            )
            row = self._select_owned(connection, user_id, resume_id)
        if row is None:
            raise ResumeNotFoundError("简历不存在")
        return _to_stored_resume(row)

    def duplicate(self, user_id: str, resume_id: str, name: str) -> StoredResume:
        copy_id = str(uuid4())
        with self._engine.begin() as connection:
            self._lock_user(connection, user_id)
            source = self._select_owned(connection, user_id, resume_id)
            if source is None:
                raise ResumeNotFoundError("简历不存在")
            connection.execute(
                _USER_RESUMES.insert().values(
                    resume_id=copy_id,
                    user_id=user_id,
                    resume_name=name,
                    resume_data_json=_normalize_data(source.get("resume_data_json")),
                    is_active=False,
                )
            )
            row = self._select_owned(connection, user_id, copy_id)
        if row is None:
            raise ResumeNotFoundError("简历不存在")
        return _to_stored_resume(row)

    def delete(self, user_id: str, resume_id: str) -> None:
        with self._engine.begin() as connection:
            self._lock_user(connection, user_id)
            target = self._select_owned(connection, user_id, resume_id)
            if target is None:
                raise ResumeNotFoundError("简历不存在")
            total = connection.scalar(
                select(func.count()).select_from(_USER_RESUMES).where(_USER_RESUMES.c.user_id == user_id)
            )
            if int(total or 0) <= 1:
                raise LastResumeDeletionError("至少需要保留一份简历")
            connection.execute(
                delete(_USER_RESUMES).where(
                    _USER_RESUMES.c.user_id == user_id,
                    _USER_RESUMES.c.resume_id == resume_id,
                )
            )
            if bool(target.get("is_active")):
                next_resume_id = connection.scalar(
                    select(_USER_RESUMES.c.resume_id)
                    .where(_USER_RESUMES.c.user_id == user_id)
                    .order_by(
                        _USER_RESUMES.c.updated_at.desc(),
                        _USER_RESUMES.c.created_at.desc(),
                    )
                    .limit(1)
                )
                if not next_resume_id:
                    raise LastResumeDeletionError("至少需要保留一份简历")
                connection.execute(
                    update(_USER_RESUMES)
                    .where(
                        _USER_RESUMES.c.user_id == user_id,
                        _USER_RESUMES.c.resume_id == next_resume_id,
                    )
                    .values(is_active=True)
                )

    def _lock_user(self, connection: Connection, user_id: str) -> None:
        statement = select(_AUTH_USERS.c.user_id).where(_AUTH_USERS.c.user_id == user_id).with_for_update()
        if connection.scalar(statement) is None:
            raise ResumeNotFoundError("登录账号不存在")

    def _select_owned(self, connection: Connection, user_id: str, resume_id: str) -> RowMapping | None:
        statement = (
            select(_USER_RESUMES)
            .where(
                _USER_RESUMES.c.user_id == user_id,
                _USER_RESUMES.c.resume_id == resume_id,
            )
            .limit(1)
        )
        return connection.execute(statement).mappings().first()


def _build_engine(config: MySqlConnectionConfig) -> Engine:
    url = URL.create(
        drivername="mysql+pymysql",
        username=config.username,
        password=config.password,
        host=config.host,
        port=config.port,
        database=config.database,
    )
    return create_engine(url, pool_pre_ping=True)


def _parse_mysql_config(datasource_url: str, username: str, password: str) -> MySqlConnectionConfig:
    safe_url = str(datasource_url or "").strip()
    if not safe_url:
        raise RuntimeError("MYSQL_DATASOURCE_URL is missing")
    normalized_url = safe_url[5:] if safe_url.startswith("jdbc:") else safe_url
    if normalized_url.startswith("mysql+pymysql://"):
        normalized_url = "mysql://" + normalized_url[len("mysql+pymysql://") :]
    parsed = urlsplit(normalized_url)
    if parsed.scheme != "mysql" or not parsed.path.lstrip("/"):
        raise RuntimeError("MYSQL_DATASOURCE_URL must include a mysql database")
    resolved_username = unquote(parsed.username or "") or str(username or "").strip()
    if not resolved_username:
        raise RuntimeError("MySQL username is missing")
    return MySqlConnectionConfig(
        host=str(parsed.hostname or "127.0.0.1"),
        port=parsed.port or 3306,
        database=parsed.path.lstrip("/"),
        username=resolved_username,
        password=unquote(parsed.password or "") or str(password or ""),
    )


def _normalize_data(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _to_stored_resume(row: RowMapping) -> StoredResume:
    return StoredResume(
        resume_id=str(row.get("resume_id") or "").strip(),
        user_id=str(row.get("user_id") or "").strip(),
        name=str(row.get("resume_name") or "").strip(),
        data=_normalize_data(row.get("resume_data_json")),
        active=bool(row.get("is_active")),
        created_at=_to_datetime(row.get("created_at")),
        updated_at=_to_datetime(row.get("updated_at")),
    )
