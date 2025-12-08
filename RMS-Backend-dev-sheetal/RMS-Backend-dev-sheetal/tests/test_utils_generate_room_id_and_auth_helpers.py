import pytest
from app.utils.generate_room_id import generate_room_id
from app.utils.authentication_helpers import is_valid_email, validate_input_email
from fastapi import HTTPException


def test_generate_room_id_deterministic():
    id1 = generate_room_id("job123", "profile456")
    id2 = generate_room_id("job123", "profile456")
    assert id1 == id2
    assert isinstance(id1, str) and len(id1) == 16


def test_generate_room_id_differs_with_input():
    a = generate_room_id("jobA", "profile1")
    b = generate_room_id("jobB", "profile1")
    assert a != b


def test_is_valid_email_true_and_false():
    assert is_valid_email("test@example.com") is True
    assert is_valid_email("not-an-email") is False


def test_validate_input_email_raises_on_invalid():
    with pytest.raises(HTTPException) as exc:
        validate_input_email("nope")
    assert exc.value.status_code == 400
