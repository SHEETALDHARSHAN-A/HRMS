import base64
from app.utils.hash_json import convert_bytes_to_base64, compute_json_hash


def test_convert_bytes_to_base64_bytes():
    b = b"hello"
    assert convert_bytes_to_base64(b) == base64.b64encode(b).decode('utf-8')


def test_convert_bytes_to_base64_nested():
    data = {"a": b"x", "b": [b"y", {"c": b"z"}]}
    res = convert_bytes_to_base64(data)
    assert res["a"] == base64.b64encode(b"x").decode('utf-8')
    assert res["b"][0] == base64.b64encode(b"y").decode('utf-8')
    assert res["b"][1]["c"] == base64.b64encode(b"z").decode('utf-8')


def test_compute_json_hash_with_data():
    data = {"x": 1, "y": "two"}
    h = compute_json_hash(data)
    # Ensure it's a 64-char hex sha256
    assert isinstance(h, str) and len(h) == 64


def test_compute_json_hash_with_empty_returns_none():
    assert compute_json_hash({}) is None
    assert compute_json_hash(None) is None
