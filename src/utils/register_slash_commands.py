import requests
import os
from dotenv import load_dotenv

load_dotenv()

APPLICATION_ID = os.getenv("DISCORD_APPLICATION_ID")
GUILD_ID = os.getenv("DISCORD_GUILD_ID")
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

url = f"https://discord.com/api/v10/applications/{APPLICATION_ID}/guilds/{GUILD_ID}/commands"

headers = {
    "Authorization": f"Bot {BOT_TOKEN}",
    "Content-Type": "application/json",
}

# data = {
#     "name": "ping",
#     "description": "Responde Pong!"
# }

commands = [
    {
        "name": "alert",
        "description": "Cria um alerta de cotação avisado por e-mail",
        "options": [
            {
                "name": "email",
                "description": "email para notificação",
                "type": 3,
                "required": True
            },
            {
                "name": "moeda",
                "description": "moeda alvo (USD-BRL, EUR-BRL, BTC-BRL)",
                "type": 3,
                "required": True
            },
            {
                "name": "valor",
                "description": "valor esperado para a notificação",
                "type": 3,
                "required": True
            },
        ]
    },
    {
        "name": "daily",
        "description": "Resumo do dia: abertura, última cotação e variação"
    },
]

# Cada comando é registrado individualmente; o endpoint de guild aceita
# um POST por comando (o PUT em lote substituiria todos de uma vez).
for command in commands:
    response = requests.post(url, headers=headers, json=command)

    print(command["name"], response.status_code)
    print(response.json())
