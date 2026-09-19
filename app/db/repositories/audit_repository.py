from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog
from app.db.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession):
        super().__init__(AuditLog, session)

    async def log_action(
        self,
        action: str,
        resource: str,
        user_id: Optional[str] = None,
        ip: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        return await self.create(
            user_id=user_id,
            action=action,
            resource=resource,
            ip=ip,
            details=details or {},
        )
