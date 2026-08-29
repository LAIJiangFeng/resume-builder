# author: jf
from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any, Iterator
from urllib.parse import unquote, urlsplit

from sqlalchemy import JSON, DateTime, Integer, String, create_engine, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.engine import URL

from app.application.ports.auth_user_repository import (
    AuthRepositoryTransaction,
    AuthUserRepository,
)
from app.domain.exceptions.auth_exceptions import (
    AuthError,
    AuthStorageError,
    AuthUserAlreadyExistsError,
    AuthVerificationWriteConflictError,
)
from app.domain.models.auth import AuthAccount, AuthEmailVerification


class _AuthBase(DeclarativeBase):
    pass


class _AuthUserRecord(_AuthBase):
    __tablename__ = "auth_users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    permissions_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    enabled: Mapped[int] = mapped_column(Integer, nullable=False)


class _AuthEmailVerificationRecord(_AuthBase):
    __tablename__ = "auth_email_verification_codes"

    email: Mapped[str] = mapped_column(String(254), primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[Any] = mapped_column(DateTime, nullable=False)
    resend_available_at: Mapped[Any] = mapped_column(DateTime, nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False)


class _SqlAlchemyAuthTransaction(AuthRepositoryTransaction):
    def __init__(self, session: Session) -> None:
        self._session = session

    def find_by_username(
        self, username: str, *, enabled_only: bool
    ) -> AuthAccount | None:
        statement = (
            select(_AuthUserRecord).where(_AuthUserRecord.username == username).limit(1)
        )
        if enabled_only:
            statement = statement.where(_AuthUserRecord.enabled == 1)
        record = self._session.scalar(statement)
        return self._to_account(record) if record is not None else None

    def create_user(self, account: AuthAccount) -> None:
        self._session.add(
            _AuthUserRecord(
                user_id=account.id,
                username=account.username,
                password_hash=account.password_hash,
                display_name=account.display_name,
                role=account.role,
                permissions_json=list(account.permissions),
                enabled=1,
            )
        )
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AuthUserAlreadyExistsError("该邮箱已注册，请直接登录") from exc

    def update_password_hash(self, user_id: str, password_hash: str) -> bool:
        record = self._session.get(_AuthUserRecord, user_id)
        if record is None or record.enabled != 1:
            return False
        record.password_hash = password_hash
        self._session.flush()
        return True

    def find_verification_for_update(self, email: str) -> AuthEmailVerification | None:
        statement = (
            select(_AuthEmailVerificationRecord)
            .where(_AuthEmailVerificationRecord.email == email)
            .limit(1)
            .with_for_update()
        )
        record = self._session.scalar(statement)
        if record is None:
            return None
        return AuthEmailVerification(
            email=record.email,
            code_hash=record.code_hash,
            expires_at=record.expires_at,
            resend_available_at=record.resend_available_at,
            failed_attempts=max(0, int(record.failed_attempts or 0)),
        )

    def save_verification(self, verification: AuthEmailVerification) -> None:
        record = self._session.get(_AuthEmailVerificationRecord, verification.email)
        if record is None:
            record = _AuthEmailVerificationRecord(
                email=verification.email,
                code_hash=verification.code_hash,
                expires_at=verification.expires_at,
                resend_available_at=verification.resend_available_at,
                failed_attempts=verification.failed_attempts,
            )
            self._session.add(record)
        else:
            record.code_hash = verification.code_hash
            record.expires_at = verification.expires_at
            record.resend_available_at = verification.resend_available_at
            record.failed_attempts = verification.failed_attempts
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise AuthVerificationWriteConflictError(
                "验证码发送过于频繁，请稍后重试"
            ) from exc

    def increment_verification_failed_attempts(self, email: str) -> None:
        record = self._session.get(_AuthEmailVerificationRecord, email)
        if record is None:
            return
        record.failed_attempts = max(0, int(record.failed_attempts or 0)) + 1
        self._session.flush()

    def delete_verification(self, email: str) -> None:
        record = self._session.get(_AuthEmailVerificationRecord, email)
        if record is None:
            return
        self._session.delete(record)
        self._session.flush()

    @staticmethod
    def _to_account(record: _AuthUserRecord) -> AuthAccount:
        return AuthAccount(
            id=str(record.user_id or "").strip(),
            username=str(record.username or "").strip().lower(),
            password_hash=str(record.password_hash or "").strip().lower(),
            display_name=str(record.display_name or "").strip(),
            role="admin"
            if str(record.role or "").strip().lower() == "admin"
            else "user",
            permissions=_normalize_permissions(record.permissions_json),
        )


class MySqlAuthUserRepository(AuthUserRepository):
    def __init__(
        self, datasource_url: str, username: str = "", password: str = ""
    ) -> None:
        sqlalchemy_url = _build_sqlalchemy_url(datasource_url, username, password)
        self._engine = create_engine(
            sqlalchemy_url,
            pool_pre_ping=True,
            connect_args={"charset": "utf8mb4"},
        )
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False)

    @contextmanager
    def transaction(self) -> Iterator[AuthRepositoryTransaction]:
        session = self._session_factory()
        try:
            with session.begin():
                yield _SqlAlchemyAuthTransaction(session)
        except AuthError:
            raise
        except SQLAlchemyError as exc:
            raise AuthStorageError("登录用户表不可用") from exc
        finally:
            session.close()


def _build_sqlalchemy_url(datasource_url: str, username: str, password: str) -> URL:
    safe_url = str(datasource_url or "").strip()
    if not safe_url:
        raise AuthStorageError("MYSQL_DATASOURCE_URL 未配置")

    normalized_url = safe_url[5:] if safe_url.startswith("jdbc:") else safe_url
    if normalized_url.startswith("mysql+pymysql://"):
        parsed_url = "mysql://" + normalized_url[len("mysql+pymysql://") :]
    else:
        parsed_url = normalized_url
    parsed = urlsplit(parsed_url)
    if parsed.scheme != "mysql":
        raise AuthStorageError("MYSQL_DATASOURCE_URL 必须使用 mysql 协议")

    database = parsed.path.lstrip("/")
    resolved_username = unquote(parsed.username or "") or str(username or "").strip()
    resolved_password = unquote(parsed.password or "") or str(password or "")
    if not database or not resolved_username:
        raise AuthStorageError("MySQL 数据库名称或账号未配置")

    return URL.create(
        drivername="mysql+pymysql",
        username=resolved_username,
        password=resolved_password,
        host=str(parsed.hostname or "127.0.0.1"),
        port=parsed.port or 3306,
        database=database,
    )


def _normalize_permissions(raw_permissions: Any) -> tuple[str, ...]:
    if isinstance(raw_permissions, str):
        try:
            raw_permissions = json.loads(raw_permissions)
        except json.JSONDecodeError:
            return ()
    if not isinstance(raw_permissions, list):
        return ()
    return tuple(
        safe_permission
        for permission in raw_permissions
        if (safe_permission := str(permission or "").strip())
    )
