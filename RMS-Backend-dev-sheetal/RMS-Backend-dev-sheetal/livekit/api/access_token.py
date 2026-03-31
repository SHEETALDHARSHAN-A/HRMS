import time
import jwt


class VideoGrants:
    def __init__(self, room=None, room_join: bool = False, can_publish: bool = False, can_subscribe: bool = False):
        self.room = room
        self.room_join = room_join
        self.can_publish = can_publish
        self.can_subscribe = can_subscribe

class AccessToken:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self._identity = None
        self._name = None
        self._grants = None

    def with_grants(self, grants: VideoGrants):
        self._grants = grants
        return self

    def with_identity(self, identity: str):
        self._identity = identity
        return self

    def with_name(self, name: str):
        self._name = name
        return self

    def to_jwt(self) -> str:
        # Create a real JWT when LiveKit credentials are provided.
        identity = self._identity or "unknown"
        if not self.api_key or not self.api_secret:
            return f"stubbed-jwt-{identity}"

        now = int(time.time())
        payload = {
            "iss": self.api_key,
            "sub": identity,
            "iat": now,
            "nbf": now,
            "exp": now + 3600,
        }

        if self._name:
            payload["name"] = self._name

        if self._grants:
            video = {}
            if self._grants.room:
                video["room"] = self._grants.room
            if self._grants.room_join:
                video["roomJoin"] = True
            if self._grants.can_publish:
                video["canPublish"] = True
            if self._grants.can_subscribe:
                video["canSubscribe"] = True

            if video:
                payload["video"] = video

        return jwt.encode(payload, self.api_secret, algorithm="HS256")
