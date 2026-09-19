from typing import Callable, List, Optional
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.errors import AuthenticationError, AuthorizationError
from app.core.security import decode_token
from app.db.models import User
from app.db.repositories.user_repository import UserRepository
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> User:
    if not credentials:
        raise AuthenticationError("Authorization header is missing")

    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Invalid token payload")

    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is deactivated")

    return user


def require_roles(allowed_roles: List[str]) -> Callable:
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AuthorizationError(
                f"Role '{current_user.role}' is not authorized. Required: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
