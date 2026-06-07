import pytest
from datetime import timedelta
from querymindai_backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from querymindai_backend.models.auth_models import UserRole, UserContext
from querymindai_backend.security import (
    can_access_admin,
    can_access_logs,
    can_access_evaluation,
    can_access_query,
)

def test_password_hash_not_plain():
    password = "SuperSecretPassword123"
    hashed = hash_password(password)
    assert hashed != password
    # check that it's a valid pbkdf2-sha256 hash signature
    assert "$pbkdf2-sha256$" in hashed or len(hashed) > 30

def test_verify_password():
    password = "SuperSecretPassword123"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False

def test_create_access_token():
    payload = {"sub": "alice", "role": UserRole.ADMIN}
    token = create_access_token(payload)
    assert isinstance(token, str)
    assert len(token.split(".")) == 3

def test_decode_access_token_success():
    payload = {"sub": "alice", "role": UserRole.ADMIN}
    token = create_access_token(payload)
    token_data = decode_access_token(token)
    assert token_data is not None
    assert token_data.username == "alice"
    assert token_data.role == UserRole.ADMIN

def test_decode_access_token_expired():
    # Create an already expired token
    payload = {"sub": "bob", "role": UserRole.DEVELOPER}
    token = create_access_token(payload, expires_delta=timedelta(seconds=-10))
    token_data = decode_access_token(token)
    assert token_data is None

def test_decode_access_token_invalid():
    assert decode_access_token("not_a_valid_token") is None

def test_rbac_admin_capabilities():
    ctx = UserContext(username="admin_user", role=UserRole.ADMIN)
    assert can_access_admin(ctx) is True
    assert can_access_logs(ctx) is True
    assert can_access_evaluation(ctx) is True
    assert can_access_query(ctx) is True

def test_rbac_developer_capabilities():
    ctx = UserContext(username="dev_user", role=UserRole.DEVELOPER)
    assert can_access_admin(ctx) is False
    assert can_access_logs(ctx) is True
    assert can_access_evaluation(ctx) is True
    assert can_access_query(ctx) is True

def test_rbac_business_user_capabilities():
    ctx = UserContext(username="biz_user", role=UserRole.BUSINESS_USER)
    assert can_access_admin(ctx) is False
    assert can_access_logs(ctx) is False
    assert can_access_evaluation(ctx) is False
    assert can_access_query(ctx) is True

def test_rbac_readonly_user_capabilities():
    ctx = UserContext(username="ro_user", role=UserRole.READONLY_USER)
    assert can_access_admin(ctx) is False
    assert can_access_logs(ctx) is False
    assert can_access_evaluation(ctx) is False
    assert can_access_query(ctx) is True

def test_require_role_allowed():
    from querymindai_backend.security import require_role
    dependency = require_role([UserRole.ADMIN, UserRole.DEVELOPER])
    ctx = UserContext(username="dev_user", role=UserRole.DEVELOPER)
    assert dependency(ctx) == ctx

def test_require_role_forbidden():
    from fastapi import HTTPException
    from querymindai_backend.security import require_role
    dependency = require_role([UserRole.ADMIN])
    ctx = UserContext(username="biz_user", role=UserRole.BUSINESS_USER)
    with pytest.raises(HTTPException) as exc_info:
        dependency(ctx)
    assert exc_info.value.status_code == 403

