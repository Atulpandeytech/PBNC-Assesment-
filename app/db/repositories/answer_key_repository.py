from typing import Optional
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AnswerKey
from app.db.repositories.base_repository import BaseRepository


class AnswerKeyRepository(BaseRepository[AnswerKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnswerKey, session)

    async def get_by_document(self, document_id: str) -> Optional[AnswerKey]:
        stmt = select(AnswerKey).where(AnswerKey.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def delete_by_document(self, document_id: str) -> int:
        stmt = delete(AnswerKey).where(AnswerKey.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.rowcount
