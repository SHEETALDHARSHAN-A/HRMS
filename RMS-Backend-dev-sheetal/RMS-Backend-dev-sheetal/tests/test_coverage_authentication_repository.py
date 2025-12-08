import pytest
from app.db.repository.authentication_repository import check_user_existence, create_user_from_cache


@pytest.mark.asyncio
async def test_check_user_existence_found(fake_db, monkeypatch):
    """Test check_user_existence when user exists"""
    from app.db.models.user_model import User
    
    mock_user = User(
        first_name="John",
        last_name="Doe",
        email="john@test.com",
        phone_number="1234567890",
        role="CANDIDATE"
    )
    
    async def mock_get_user_by_email(db, email):
        return mock_user
    
    monkeypatch.setattr('app.db.repository.authentication_repository.get_user_by_email', mock_get_user_by_email)
    
    result = await check_user_existence(fake_db, "john@test.com")
    assert result == mock_user


@pytest.mark.asyncio
async def test_check_user_existence_not_found(fake_db, monkeypatch):
    """Test check_user_existence when user does not exist"""
    async def mock_get_user_by_email(db, email):
        return None
    
    monkeypatch.setattr('app.db.repository.authentication_repository.get_user_by_email', mock_get_user_by_email)
    
    result = await check_user_existence(fake_db, "nonexistent@test.com")
    assert result is None


@pytest.mark.asyncio
async def test_create_user_from_cache_with_role(fake_db, monkeypatch):
    """Test create_user_from_cache with explicit role"""
    from app.db.models.user_model import User
    
    user_details = {
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@test.com",
        "phone_number": "9876543210",
        "role": "ADMIN"
    }
    
    created_user = None
    
    async def mock_create_user(db, user):
        nonlocal created_user
        created_user = user
        return user
    
    monkeypatch.setattr('app.db.repository.authentication_repository.create_user', mock_create_user)
    
    result = await create_user_from_cache(fake_db, user_details)
    
    assert created_user is not None
    assert created_user.first_name == "Jane"
    assert created_user.last_name == "Smith"
    assert created_user.email == "jane@test.com"
    assert created_user.phone_number == "9876543210"
    assert created_user.role == "ADMIN"


@pytest.mark.asyncio
async def test_create_user_from_cache_default_role(fake_db, monkeypatch):
    """Test create_user_from_cache with default CANDIDATE role - covers line 15"""
    from app.db.models.user_model import User
    
    user_details = {
        "first_name": "Bob",
        "last_name": "Johnson",
        "email": "bob@test.com",
        "phone_number": "5555555555"
        # No role specified - should default to CANDIDATE
    }
    
    created_user = None
    
    async def mock_create_user(db, user):
        nonlocal created_user
        created_user = user
        return user
    
    monkeypatch.setattr('app.db.repository.authentication_repository.create_user', mock_create_user)
    
    result = await create_user_from_cache(fake_db, user_details)
    
    assert created_user is not None
    assert created_user.role == "CANDIDATE"  # Default role
    assert created_user.first_name == "Bob"
    assert created_user.email == "bob@test.com"
