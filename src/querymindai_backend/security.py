from typing import List, Callable, Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from querymindai_backend.models.auth_models import UserRole, UserContext
from querymindai_backend.auth import decode_access_token

# Bearer token authentication scheme
security_scheme = HTTPBearer(auto_error=False)

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_scheme)) -> UserContext:
    """
    Dependency to retrieve the current authenticated user context from JWT token.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    token_data = decode_access_token(token)
    if not token_data or not token_data.username or not token_data.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return UserContext(username=token_data.username, role=token_data.role)

def require_role(allowed_roles: List[UserRole]) -> Callable[[UserContext], UserContext]:
    """
    Dependency wrapper that enforces the user to have one of the allowed roles.
    """
    def dependency(current_user: UserContext = Security(get_current_user)) -> UserContext:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operation not permitted",
            )
        return current_user
    return dependency

def can_access_admin(user_context: UserContext) -> bool:
    """
    Only admin role has access to full admin config settings.
    """
    return user_context.role == UserRole.ADMIN

def can_access_logs(user_context: UserContext) -> bool:
    """
    Admin and developer roles can access query logs.
    """
    return user_context.role in [UserRole.ADMIN, UserRole.DEVELOPER]

def can_access_evaluation(user_context: UserContext) -> bool:
    """
    Admin and developer roles can access evaluation tools.
    """
    return user_context.role in [UserRole.ADMIN, UserRole.DEVELOPER]

def can_access_query(user_context: UserContext) -> bool:
    """
    All roles can perform natural language database queries.
    """
    return user_context.role in [
        UserRole.ADMIN,
        UserRole.DEVELOPER,
        UserRole.BUSINESS_USER,
        UserRole.READONLY_USER
    ]
