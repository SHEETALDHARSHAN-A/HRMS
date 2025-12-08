from .access_token import AccessToken, VideoGrants

class LiveKitAPI:
    """Minimal test stub of LiveKitAPI used in tests.

    Provides a `room` attribute with an async `create_room` method.
    """
    def __init__(self, url: str, api_key: str, api_secret: str):
        self.url = url
        self.api_key = api_key
        self.api_secret = api_secret
        self.room = self.RoomAPI()

    class RoomAPI:
        async def create_room(self, req):
            # No-op stub: emulate successful creation
            return {"name": getattr(req, 'name', None)}

__all__ = ["LiveKitAPI", "AccessToken", "VideoGrants"]
