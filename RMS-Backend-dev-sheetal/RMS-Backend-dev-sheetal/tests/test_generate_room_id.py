import pytest

from app.utils.generate_room_id import generate_room_id


def test_generate_room_id_consistent():
    a = generate_room_id("job-123", "profile-abc")
    b = generate_room_id("job-123", "profile-abc")
    assert a == b


def test_generate_room_id_different_for_different_inputs():
    a = generate_room_id("job-1", "profile-1")
    b = generate_room_id("job-2", "profile-1")
    assert a != b


def test_generate_room_id_length():
    rid = generate_room_id("j", "p")
    assert isinstance(rid, str)
    assert len(rid) == 16
