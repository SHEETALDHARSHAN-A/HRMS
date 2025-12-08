# src/utils/hash_file.py

import hashlib

def compute_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()