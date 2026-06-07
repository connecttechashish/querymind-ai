import pytest
from pydantic import ValidationError
from querymindai_backend.models.auth_models import UserRole, TokenData, UserContext

def test_user_role_enum():
    assert UserRole.ADMIN == "admin"
    assert UserRole.DEVELOPER == "developer"
    assert UserRole.BUSINESS_USER == "business_user"
    assert UserRole.READONLY_USER == "readonly_user"
    
    # Test valid choices
    roles = [role.value for role in UserRole]
    assert "admin" in roles
    assert "developer" in roles
    assert "business_user" in roles
    assert "readonly_user" in roles

def test_token_data_model():
    # TokenData fields are optional
    token = TokenData()
    assert token.username is None
    assert token.role is None
    
    token_with_data = TokenData(username="testuser", role=UserRole.ADMIN)
    assert token_with_data.username == "testuser"
    assert token_with_data.role == UserRole.ADMIN

def test_user_context_model():
    # UserContext fields are required
    with pytest.raises(ValidationError):
        UserContext()
        
    with pytest.raises(ValidationError):
        UserContext(username="testuser")
        
    context = UserContext(username="testuser", role=UserRole.BUSINESS_USER)
    assert context.username == "testuser"
    assert context.role == UserRole.BUSINESS_USER
    
    # Validation fails on invalid roles
    with pytest.raises(ValidationError):
        UserContext(username="testuser", role="invalid_role")
