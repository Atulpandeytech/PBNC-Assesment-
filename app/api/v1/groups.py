from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.document import DocumentResponse
from app.schemas.group import (
    AttachDocumentRequest,
    DocumentGroupResponse,
    GroupCreateRequest,
    MergedQuestionsResponse,
)
from app.services.group_service import GroupService

router = APIRouter(prefix="/groups", tags=["Document Groups"])


@router.post("", response_model=DocumentGroupResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=DocumentGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    req: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Create a new logical document group (e.g. associating Question Paper with Answer Key)."""
    service = GroupService(session)
    group = await service.create_group(req.name, current_user)
    return DocumentGroupResponse(
        id=group.id,
        owner_id=group.owner_id,
        name=group.name,
        created_at=group.created_at,
        documents=[],
    )


@router.get("", response_model=List[DocumentGroupResponse])
@router.get("/", response_model=List[DocumentGroupResponse])
async def list_groups(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """List all document groups owned by current user."""
    service = GroupService(session)
    groups = await service.list_groups(current_user)
    return [
        DocumentGroupResponse(
            id=g.id,
            owner_id=g.owner_id,
            name=g.name,
            created_at=g.created_at,
            documents=[DocumentResponse.model_validate(d) for d in g.documents],
        )
        for g in groups
    ]


@router.get("/{group_id}", response_model=DocumentGroupResponse)
async def get_group(
    group_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve group details along with attached documents and their roles."""
    service = GroupService(session)
    group = await service.get_group(group_id, current_user)
    return DocumentGroupResponse(
        id=group.id,
        owner_id=group.owner_id,
        name=group.name,
        created_at=group.created_at,
        documents=[DocumentResponse.model_validate(d) for d in group.documents],
    )


@router.post("/{group_id}/documents", response_model=DocumentResponse)
async def attach_document_to_group(
    group_id: str,
    req: AttachDocumentRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Attach a document to a group with a specific role (question_paper, answer_key) and trigger re-association."""
    service = GroupService(session)
    doc = await service.attach_document(group_id, req.document_id, req.role, current_user)
    return DocumentResponse.model_validate(doc)


@router.delete("/{group_id}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_document_from_group(
    group_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Remove a document from a group."""
    service = GroupService(session)
    await service.detach_document(group_id, document_id, current_user)
    return None


@router.get("/{group_id}/questions", response_model=MergedQuestionsResponse)
@router.post("/{group_id}/merge", response_model=MergedQuestionsResponse)
@router.post("/{group_id}/merge/", response_model=MergedQuestionsResponse)
async def get_group_merged_questions(
    group_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    """Retrieve merged view of questions with answers automatically linked from the separate answer key document."""
    service = GroupService(session)
    return await service.get_merged_questions(group_id, current_user)
