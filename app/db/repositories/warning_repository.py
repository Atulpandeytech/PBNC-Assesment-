from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ExtractionWarning
from app.db.repositories.base_repository import BaseRepository


class WarningRepository(BaseRepository[ExtractionWarning]):
    def __init__(self, session: AsyncSession):
        super().__init__(ExtractionWarning, session)

    async def list_by_document(self, document_id: str) -> List[ExtractionWarning]:
        stmt = (
            select(ExtractionWarning)
            .where(ExtractionWarning.document_id == document_id)
            .order_by(ExtractionWarning.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: str) -> int:
        stmt = delete(ExtractionWarning).where(ExtractionWarning.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.rowcount
