"""Alertas de cotação: cadastro, disparo e histórico de mensagens."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.integrations.notifier import send_notification
from src.models.messages import Message
from src.models.user_coins import UserCoins
from src.models.users import User
from src.schemas.alert_schema import AlertCreate
from src.schemas.quote_schema import Quote
from src.services.coin_service import get_last_conversion_registered

# Moeda de destino das cotações monitoradas.
ALERT_TARGET = 'BRL'


class AlertAlreadyReachedError(Exception):
    """O valor escolhido já está valendo no momento do cadastro."""


async def create_alert(
    db: AsyncSession,
    user_id: int,
    data: AlertCreate
) -> UserCoins:
    """Cadastra o valor-alvo escolhido pelo usuário,
    mas também define se espera uma queda ou uma subida."""

    origin, target = data.coin_name.split('-')

    current_value = await get_last_conversion_registered(
        db, origin, target
    )

    if float(data.target_value_expected) > current_value:
        expect = 'UP'
    else:
        expect = 'DOWN'

    alert = UserCoins(
        user_id=user_id,
        coin_name=data.coin_name,
        target_value_expected=str(data.target_value_expected),
        expect=expect
    )

    db.add(alert)

    await db.commit()
    await db.refresh(alert)

    return alert


async def list_all_alerts_from_user(
    db: AsyncSession, user_id: int
) -> list[UserCoins]:
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


async def list_all_messages_from_user(
    db: AsyncSession, user_id: int
) -> list[Message]:
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

    return list(result.all())  # type:ignore


def should_notify(target: float, expect: str, bid: float) -> bool:
    match expect:
        case "UP":
            if bid >= target:
                return True
        case "DOWN":
            if bid <= target:
                return True

    return False


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
        quote = by_coin.get(alert.coin_name)  # type:ignore

        if quote is None:
            continue

        target = float(alert.target_value_expected)

        if not should_notify(target, alert.expect, quote.bid):  # type: ignore
            continue

        message = Message(
            user_id=user.id,
            message=build_alert_message(alert, quote)
        )

        db.add(message)

        # Marca antes do commit para que o alerta não dispare de novo
        # no próximo ciclo, mesmo se a notificação falhar.
        alert.notified_at = datetime.now(timezone.utc)  # type:ignore

        triggered.append((message, user))

    if not triggered:
        return []

    await db.commit()

    for message, user in triggered:
        try:
            await send_notification(user.email, message.message)  # type:ignore

        except Exception as error:
            # A mensagem já está salva; o usuário a vê pelo histórico.
            print(f'[alerts] falha ao notificar {user.email}: {error}')

    return [message for message, _ in triggered]
