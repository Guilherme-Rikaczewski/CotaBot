from src.schemas.discord import (
    DiscordInteraction,
)
from src.services.alert_bot_service import AlertBotService
from src.utils.response_builder import ResponseBuilder
from sqlalchemy.ext.asyncio import AsyncSession


class CommandDispatcher:
    def __init__(self):
        self.handlers = {
            "alert": AlertBotService()
        }

    async def dispatch(
        self,
        interaction: DiscordInteraction,
        db: AsyncSession
    ):
        if not interaction.data:
            return ResponseBuilder.message("Comando invalido.")

        command = interaction.data.name

        handler = self.handlers.get(command)
        if not handler:
            return ResponseBuilder.message("Comando invalido.")
        return await handler.execute(interaction, db)
