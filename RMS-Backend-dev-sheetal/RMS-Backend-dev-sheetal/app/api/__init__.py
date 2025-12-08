from fastapi import APIRouter
import pkgutil
import importlib

api_router = APIRouter()

package_name = __name__ 

for _, module_name, _ in pkgutil.iter_modules(__path__):
    module = importlib.import_module(f"{package_name}.{module_name}")
    router_name = f"{module_name}_router"  # expects v1_router, v2_router, etc.
    if hasattr(module, router_name):
        api_router.include_router(getattr(module, router_name), prefix=f"/{module_name}")
