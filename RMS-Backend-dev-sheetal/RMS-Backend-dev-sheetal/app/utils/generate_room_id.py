# app/utils/generate_room_id.py

import hashlib

def generate_room_id(job_id: str, profile_id: str) -> str:
    """Generates a consistent, short, pseudo-unique room ID (token) by hashing job_id and profile_id."""
    hash_input = f"{job_id}-{profile_id}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()[:16]