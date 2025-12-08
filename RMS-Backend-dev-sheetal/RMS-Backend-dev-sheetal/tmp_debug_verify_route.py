import asyncio, traceback
from app.api.v1.authentication_routes import verify_name_update_endpoint_name
from types import SimpleNamespace

async def run():
    db = SimpleNamespace()
    cache = SimpleNamespace()
    try:
        res = await verify_name_update_endpoint_name('u1','tok', db=db, cache=cache)
        print('Res type:', type(res))
        print('Res:', res)
    except Exception as e:
        traceback.print_exc()
        print('Exception:', e)

if __name__ == '__main__':
    asyncio.run(run())
