# app/utils/hash_json.py

import json
import base64
import hashlib

def convert_bytes_to_base64(obj):
    if isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    elif isinstance(obj, dict):
        return {key: convert_bytes_to_base64(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_bytes_to_base64(item) for item in obj]
    else:
        return obj
    
def compute_json_hash(data):
    # Convert any bytes in data to base64 before serializing
    data = convert_bytes_to_base64(data)
    # Now serialize to JSON and hash it
    return hashlib.sha256(json.dumps(data).encode('utf-8')).hexdigest() if data else None