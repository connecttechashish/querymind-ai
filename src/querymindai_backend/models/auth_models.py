from enum import Enum
from pydantic import BaseModel
from typing import Optional

class UserRole(str, Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    BUSINESS_USER = "business_user"
    READONLY_USER = "readonly_user"

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None

class UserContext(BaseModel):
    username: str
    role: UserRole
