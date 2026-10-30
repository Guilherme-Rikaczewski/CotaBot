# type: ignore
from src.schemas.discord import (
    DiscordInteraction,
)
from src.services.base_service import BaseService
from src.utils.response_builder import ResponseBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.alert_schema import AlertCreate
from src.services.alert_service import create_alert_by_bot
from src.services.coin_service import DAILY_TIMEZONE, get_daily_summary
from src.setup.seed_coins import SEED_ORIGINS as TRACKED_ORIGINS
from datetime import datetime


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


def _format_brl(value: float) -> str:
    """Formata no padrão brasileiro: 5.44 -> 5,44 | 413324.0 -> 413.324,00"""
    texto = f'{value:,.2f}'

    return texto.replace(',', '#').replace('.', ',').replace('#', '.')


def _format_variation(variation: float) -> str:
    seta = '📈' if variation > 0 else '📉' if variation < 0 else '➖'
    sinal = '+' if variation > 0 else ''

    return f'{sinal}{variation:.2f}'.replace('.', ',') + f'% {seta}'


class DailyBotService(BaseService):
    """Resumo do dia das moedas monitoradas, em resposta ao /daily."""

    async def execute(
        self,
        interaction: DiscordInteraction,
        db: AsyncSession
    ):
        summary = await get_daily_summary(db, TRACKED_ORIGINS)

        hoje = datetime.now(DAILY_TIMEZONE).strftime('%d/%m/%Y')

        linhas = [f' **Resumo do dia — {hoje}**', '']

        for item in summary:
            par = f"{item['coin']}/{item['target']}"

            # Sem registro hoje: a moeda não é negociada no fim de
            # semana ou o coletor ainda não rodou desde a meia-noite.
            if item['opening'] is None or item['closing'] is None:
                linhas.append(f'**{par}** — sem cotação registrada hoje.')
                linhas.append('')
                continue

            linhas.append(f'**{par}**')
            linhas.append(
                f"Abertura: R$ {_format_brl(item['opening'])}"
            )
            linhas.append(
                f"Última: R$ {_format_brl(item['closing'])}"
            )
            linhas.append(
                f"Variação: {_format_variation(item['variation'])}"
            )
            linhas.append('')

        linhas.append(
            '_"Última" é a cotação mais recente do dia; '
            'enquanto o dia corre, ainda não é o fechamento._'
        )

        return ResponseBuilder.message('\n'.join(linhas))

