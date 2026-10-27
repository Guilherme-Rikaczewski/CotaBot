# type: ignore
from src.schemas.discord import (
    DiscordInteraction,
)
from src.services.base_service import BaseService
from src.utils.response_builder import ResponseBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.alert_schema import AlertCreate
from src.services.alert_service import create_alert_by_bot


class AlertBotService(BaseService):
    async def execute(
        self,
        interaction: DiscordInteraction,
        db: AsyncSession
    ):
        if not interaction.data.options:
            return ResponseBuilder.message("Comando invalido.")

        email = interaction.data.options[0].value
        coin = interaction.data.options[1].value
        target = interaction.data.options[2].value
        try:
            alert = await create_alert_by_bot(
                db,
                email,
                AlertCreate(
                    coin_name=coin,
                    target_value_expected=target
                )
            )

            if not alert:
                raise ValueError("Não conseguiu criar o alerta")

        except ValueError as error:
            return ResponseBuilder.message(f'{error.args[0]}, lista: {interaction.data.options}')

        return ResponseBuilder.message(
            f"Alerta cadastrado para o email: {email}"
        )

