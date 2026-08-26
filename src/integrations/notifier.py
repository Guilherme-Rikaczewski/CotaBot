"""Entrega das notificações de alerta ao usuário.

Por ora a notificação apenas é registrada em log — a mensagem em si já
fica persistida na tabela `messages`. O envio por e-mail entra aqui:
basta implementar o corpo de `send_notification` (SMTP, provedor
transacional, fila etc.) sem tocar na lógica de alertas.
"""
import logging

logger = logging.getLogger(__name__)


async def send_notification(email: str, message: str) -> bool:
    """Entrega a mensagem ao usuário.

    Devolve True quando a notificação foi entregue. Falhas não devem
    levantar exceção: o alerta já foi gravado e o coletor precisa
    seguir para os próximos usuários.
    """
    # TODO: enviar por e-mail. Enquanto isso, o log serve de trilha.
    logger.info('[notify] para %s: %s', email, message)

    print(f'[notify] {email}: {message}')

    return True
