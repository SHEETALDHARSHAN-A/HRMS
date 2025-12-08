from abc import ABC, abstractmethod
from typing import Dict

class BaseProcessor(ABC):

    @abstractmethod
    async def invoke(job: Dict) -> Dict:
        pass
