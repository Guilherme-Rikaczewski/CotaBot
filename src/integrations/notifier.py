"""Entrega das notificações de alerta ao usuário, por e-mail.

A configuração vem do `.env` (SMTP_HOST, SMTP_PORT, SMTP_USER,
SMTP_PASSWORD, SMTP_FROM). Sem ela o envio é apenas registrado em log e
a aplicação segue normalmente — a mensagem já está persistida em
`messages`, então o usuário continua vendo o aviso pelo site.
"""
import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=ENV_PATH)

SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_FROM = os.getenv('SMTP_FROM') or SMTP_USER
SMTP_TIMEOUT = float(os.getenv('SMTP_TIMEOUT', '15'))

# Porta 465 fala TLS desde o primeiro byte (SMTP_SSL); as demais abrem
# em texto puro e sobem para TLS com STARTTLS.
SMTP_SSL_PORT = 465

EMAIL_SUBJECT = 'CotaBot: sua cotação atingiu o valor desejado'

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """Indica se há servidor SMTP e remetente configurados."""
    return bool(SMTP_HOST and SMTP_FROM)


def _build_email(email: str, message: str) -> EmailMessage:
    mail = EmailMessage()

    mail['Subject'] = EMAIL_SUBJECT
    mail['From'] = SMTP_FROM
    mail['To'] = email

    mail.set_content(
        f'{message}\n\n'
        f'Você recebeu este aviso porque cadastrou um alerta no CotaBot.\n'
    )

    return mail


def _send_sync(email: str, message: str) -> None:
    """Envio bloqueante — roda fora do laço de eventos."""
    mail = _build_email(email, message)

    if SMTP_PORT == SMTP_SSL_PORT:
        server = smtplib.SMTP_SSL(
            SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT
        )
    else:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)

    with server:
        if SMTP_PORT != SMTP_SSL_PORT:
            server.starttls()

        # Servidor local de testes costuma não exigir autenticação.
        if SMTP_USER and SMTP_PASSWORD:
            server.login(SMTP_USER, SMTP_PASSWORD)

        server.send_message(mail)


async def send_notification(email: str, message: str) -> bool:
    """Entrega a mensagem ao usuário.

    Devolve True quando a notificação foi entregue. Falhas não devem
    levantar exceção: o alerta já foi gravado e o coletor precisa
    seguir para os próximos usuários.
    """
    if not is_configured():
        logger.info(
            '[notify] SMTP não configurado; apenas registrando. '
            'Para %s: %s',
            email,
            message
        )

        return False

    try:
        # `smtplib` é bloqueante: numa thread, para não travar o
        # coletor nem as requisições enquanto o e-mail é enviado.
        await asyncio.to_thread(_send_sync, email, message)

        logger.info('[notify] e-mail enviado para %s', email)

        return True

    except Exception as error:
        logger.warning(
            '[notify] falha ao enviar e-mail para %s: %s', email, error
        )

        return False
