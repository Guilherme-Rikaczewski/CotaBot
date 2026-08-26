"""Alertas de cotação: cadastro, disparo e histórico de mensagens."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.awesome_api import get_last_quote
from src.integrations.notifier import send_notification
from src.models.messages import Message
from src.models.user_coins import UserCoins
from src.models.users import User
from src.schemas.alert_schema import AlertCreate
from src.schemas.quote_schema import Quote

# Moeda de destino das cotações monitoradas.
ALERT_TARGET = 'BRL'


class AlertAlreadyReachedError(Exception):
    """O valor escolhido já está valendo no momento do cadastro."""


async def create_alert(
    db: AsyncSession,
    user_id: int,
    data: AlertCreate
) -> UserCoins:
    """Cadastra o valor-alvo escolhido pelo usuário.

    Recusa alvos que a cotação atual já atingiu — nesse caso o alerta
    dispararia no primeiro ciclo, o que não é o que o usuário quis
    dizer ao pedir para ser avisado quando o valor for atingido.
    """
    quote = await get_last_quote(data.coin_name, ALERT_TARGET)

    if quote.bid >= data.target_value_expected:
        raise AlertAlreadyReachedError(
            f'{data.coin_name} já está em {quote.bid}, '
            f'igual ou acima do alvo {data.target_value_expected}'
        )

    alert = UserCoins(
        user_id=user_id,
        coin_name=data.coin_name,
        target_value_expected=str(data.target_value_expected)
    )

    db.add(alert)

    await db.commit()
    await db.refresh(alert)

    return alert


async def list_alerts(db: AsyncSession, user_id: int) -> list[UserCoins]:
    result = await db.execute(
        select(UserCoins)
        .where(UserCoins.user_id == user_id)
        .order_by(UserCoins.created_at.desc())
    )

    return list(result.scalars().all())


async def delete_alert(db: AsyncSession, user_id: int, alert_id: int) -> bool:
    result = await db.execute(
        select(UserCoins).where(
            UserCoins.id == alert_id,
            UserCoins.user_id == user_id
        )
    )

    alert = result.scalar_one_or_none()

    if alert is None:
        return False

    await db.delete(alert)
    await db.commit()

    return True


async def list_messages(db: AsyncSession, user_id: int) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
    )

    return list(result.scalars().all())


def build_alert_message(alert: UserCoins, quote: Quote) -> str:
    return (
        f'{alert.coin_name}/{ALERT_TARGET} atingiu o valor desejado: '
        f'{quote.bid} (alvo: {alert.target_value_expected}). '
        f'Variação de {quote.pct_change}% no dia.'
    )


async def _pending_alerts(db: AsyncSession) -> list[tuple[UserCoins, User]]:
    """Alertas ainda não avisados, junto do usuário dono de cada um."""
    result = await db.execute(
        select(UserCoins, User)
        .join(User, User.id == UserCoins.user_id)
        .where(UserCoins.notified_at.is_(None))
    )

    return list(result.all())


async def check_alerts(
    db: AsyncSession,
    quotes: dict[str, Quote]
) -> list[Message]:
    """Dispara os alertas cujo valor-alvo foi atingido.

    Recebe as cotações já buscadas pelo coletor (indexadas por par, no
    formato "USD-BRL") para não gastar requisição extra na AwesomeAPI.
    Para cada alvo atingido: grava a mensagem, marca o alerta como
    avisado e envia a notificação.
    """
    pending = await _pending_alerts(db)

    if not pending:
        return []

    by_coin = {
        pair.split('-')[0]: quote
        for pair, quote in quotes.items()
    }

    triggered: list[tuple[Message, User]] = []

    for alert, user in pending:
        quote = by_coin.get(alert.coin_name)

        if quote is None:
            continue

        if quote.bid < float(alert.target_value_expected):
            continue

        message = Message(
            user_id=user.id,
            message=build_alert_message(alert, quote)
        )

        db.add(message)

        # Marca antes do commit para que o alerta não dispare de novo
        # no próximo ciclo, mesmo se a notificação falhar.
        alert.notified_at = datetime.now(timezone.utc)

        triggered.append((message, user))

    if not triggered:
        return []

    await db.commit()

    for message, user in triggered:
        try:
            await send_notification(user.email, message.message)

        except Exception as error:
            # A mensagem já está salva; o usuário a vê pelo histórico.
            print(f'[alerts] falha ao notificar {user.email}: {error}')

    return [message for message, _ in triggered]
