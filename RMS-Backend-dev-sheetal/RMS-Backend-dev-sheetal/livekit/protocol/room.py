class CreateRoomRequest:
    def __init__(self, name: str, empty_timeout: int = None, max_participants: int = None):
        self.name = name
        self.empty_timeout = empty_timeout
        self.max_participants = max_participants
