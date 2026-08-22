# author: jf
from __future__ import annotations

from typing import Any

from app.application.ports.resume_repository import ResumeRepository, StoredResume


class ResumeService:
    def __init__(self, repository: ResumeRepository) -> None:
        self._repository = repository

    def list_resumes(self, user_id: str) -> list[StoredResume]:
        # 列表流程只使用登录上下文中的用户 ID，仓储层会再次把用户 ID 写入查询条件。
        return self._repository.list_by_user(self._require_user_id(user_id))

    def get_resume(self, user_id: str, resume_id: str) -> StoredResume:
        safe_user_id = self._require_user_id(user_id)
        safe_resume_id = self._require_resume_id(resume_id)
        resume = self._repository.get_owned(safe_user_id, safe_resume_id)
        if resume is None:
            from app.application.ports.resume_repository import ResumeNotFoundError

            raise ResumeNotFoundError("简历不存在")
        return resume

    def create_resume(self, user_id: str, name: str | None, data: dict[str, Any] | None) -> StoredResume:
        # 新建流程由仓储事务判断是否为账号首份简历，避免并发请求产生多个当前简历。
        return self._repository.create(
            self._require_user_id(user_id),
            self._normalize_name(name, "我的简历"),
            self._normalize_data(data),
        )

    def update_resume(
        self,
        user_id: str,
        resume_id: str,
        name: str | None,
        data: dict[str, Any] | None,
    ) -> StoredResume:
        current = self.get_resume(user_id, resume_id)
        return self._repository.update(
            current.user_id,
            current.resume_id,
            self._normalize_name(name, current.name),
            self._normalize_data(data),
        )

    def activate_resume(self, user_id: str, resume_id: str) -> StoredResume:
        current = self.get_resume(user_id, resume_id)
        return self._repository.activate(current.user_id, current.resume_id)

    def duplicate_resume(self, user_id: str, resume_id: str) -> StoredResume:
        source = self.get_resume(user_id, resume_id)
        return self._repository.duplicate(source.user_id, source.resume_id, self._copy_name(source.name))

    def delete_resume(self, user_id: str, resume_id: str) -> None:
        current = self.get_resume(user_id, resume_id)
        # 删除和当前简历补选必须由同一数据库事务完成，避免账号短暂失去当前简历。
        self._repository.delete(current.user_id, current.resume_id)

    def _normalize_name(self, name: str | None, fallback: str) -> str:
        safe_name = str(name or "").strip() or str(fallback or "").strip()
        if not safe_name:
            raise ValueError("简历名称不能为空")
        if len(safe_name) > 80:
            raise ValueError("简历名称不能超过 80 个字符")
        return safe_name

    def _copy_name(self, name: str) -> str:
        suffix = " - 副本"
        safe_name = self._normalize_name(name, "我的简历")
        return f"{safe_name[: 80 - len(suffix)]}{suffix}"

    def _normalize_data(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError("简历数据必须是 JSON 对象")
        return data

    def _require_user_id(self, user_id: str) -> str:
        safe_user_id = str(user_id or "").strip()
        if not safe_user_id:
            raise ValueError("请先登录后再管理简历")
        return safe_user_id

    def _require_resume_id(self, resume_id: str) -> str:
        safe_resume_id = str(resume_id or "").strip()
        if not safe_resume_id or len(safe_resume_id) > 64:
            from app.application.ports.resume_repository import ResumeNotFoundError

            raise ResumeNotFoundError("简历不存在")
        return safe_resume_id
