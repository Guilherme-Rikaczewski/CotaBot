from abc import ABC, abstractmethod
from src.schemas.discord import (
    DiscordInteraction,
)


class BaseService(ABC):
    @abstractmethod
    async def execute(self, interaction: DiscordInteraction):
        pass
