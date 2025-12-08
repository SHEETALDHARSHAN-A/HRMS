# src/utils/async_manager.py

import gc
from contextlib import asynccontextmanager

@asynccontextmanager
async def managed_resource(resource):
    """Generic context manager for resource cleanup (async version)"""
    try:
        yield resource
    finally:
        # If resource has an async close method, await it
        if hasattr(resource, 'close'):
            await resource.close()  # await the close method if it's async
        del resource
        gc.collect()