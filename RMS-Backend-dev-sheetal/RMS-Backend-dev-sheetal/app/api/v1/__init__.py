from fastapi import APIRouter
import pkgutil
import importlib
import inspect

from .ws_routes import ws_router
from . import interview_routes

v1_router = APIRouter()

for _, module_name, _ in pkgutil.iter_modules(__path__):
    try:
        module = importlib.import_module(f"{__name__}.{module_name}")        
        for attr_name, attr_value in inspect.getmembers(module, lambda x: isinstance(x, APIRouter)):
            v1_router.include_router(attr_value)
    except Exception as e:
        import traceback
        traceback.print_exc()
v1_router.include_router(ws_router)
v1_router.include_router(interview_routes.router)

print(f"Total routes in v1_router: {len(v1_router.routes)}")
 