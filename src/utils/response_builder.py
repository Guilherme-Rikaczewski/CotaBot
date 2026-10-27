from src.schemas.discord import (
    DiscordInteractionResponse,
    DiscordInteractionResponseData,
    InteractionCallbackType
)


class ResponseBuilder:
    @staticmethod
    def message(text: str):
        return DiscordInteractionResponse(
            type=InteractionCallbackType.CHANNEL_MESSAGE_WITH_SOURCE,
            data=DiscordInteractionResponseData(
                content=text
            )
        )

    @staticmethod
    def pong():
        return DiscordInteractionResponse(
            type=InteractionCallbackType.PONG,
            data=DiscordInteractionResponseData(
                content="PINGOU."
            )
        )
