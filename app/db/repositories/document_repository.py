from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Document, DocumentPage
from app.db.repositories.base_repository import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_id_and_owner(self, document_id: str, owner_id: str) -> Optional[Document]:
        stmt = (
            select(Document)
            .where(Document.id == document_id, Document.owner_id == owner_id)
            .options(selectinload(Document.pages))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_owner_and_sha256(self, owner_id: str, sha256: str) -> Optional[Document]:
        stmt = select(Document).where(Document.owner_id == owner_id, Document.sha256 == sha256)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_owner(
        self,
        owner_id: str,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[Document], int]:
        query = select(Document).where(Document.owner_id == owner_id)
        count_query = select(func.count(Document.id)).where(Document.owner_id == owner_id)

        if status:
            query = query.where(Document.status == status)
            count_query = count_query.where(Document.status == status)

        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * limit
        query = query.order_by(Document.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_pages(self, document_id: str) -> List[DocumentPage]:
        stmt = (
            select(DocumentPage)
            .where(DocumentPage.document_id == document_id)
            .order_by(DocumentPage.page_no.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_page_by_number(self, document_id: str, page_no: int) -> Optional[DocumentPage]:
        stmt = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_no == page_no
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
