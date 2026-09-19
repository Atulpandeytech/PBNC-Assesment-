from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import DocumentGroup
from app.db.repositories.base_repository import BaseRepository


class GroupRepository(BaseRepository[DocumentGroup]):
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentGroup, session)

    async def get_with_documents(self, group_id: str) -> Optional[DocumentGroup]:
        stmt = (
            select(DocumentGroup)
            .where(DocumentGroup.id == group_id)
            .options(selectinload(DocumentGroup.documents))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_owner(self, owner_id: str) -> List[DocumentGroup]:
        stmt = (
            select(DocumentGroup)
            .where(DocumentGroup.owner_id == owner_id)
            .options(selectinload(DocumentGroup.documents))
            .order_by(DocumentGroup.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
