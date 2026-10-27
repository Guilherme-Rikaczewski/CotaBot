from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field


class InteractionType(IntEnum):
    PING = 1
    APPLICATION_COMMAND = 2
    MESSAGE_COMPONENT = 3
    APPLICATION_COMMAND_AUTOCOMPLETE = 4
    MODAL_SUBMIT = 5


class InteractionCallbackType(IntEnum):
    PONG = 1
    CHANNEL_MESSAGE_WITH_SOURCE = 4
    DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
    DEFERRED_UPDATE_MESSAGE = 6
    UPDATE_MESSAGE = 7
    APPLICATION_COMMAND_AUTOCOMPLETE_RESULT = 8
    MODAL = 9


class CommandOptionType(IntEnum):
    SUB_COMMAND = 1
    SUB_COMMAND_GROUP = 2
    STRING = 3
    INTEGER = 4
    BOOLEAN = 5
    USER = 6
    CHANNEL = 7
    ROLE = 8
    MENTIONABLE = 9
    NUMBER = 10
    ATTACHMENT = 11


class DiscordUser(BaseModel):
    id: str
    username: str


class DiscordMember(BaseModel):
    user: DiscordUser
    nick: str | None = None


class DiscordCommandOption(BaseModel):
    name: str
    type: CommandOptionType
    value: Any


class DiscordInteractionData(BaseModel):
    id: str
    name: str
    type: int
    options: list[DiscordCommandOption] = Field(default_factory=list)


class DiscordInteraction(BaseModel):
    id: str
    application_id: str
    type: InteractionType
    token: str
    version: int

    guild_id: str | None = None
    channel_id: str | None = None

    member: DiscordMember | None = None
    user: DiscordUser | None = None

    data: DiscordInteractionData | None = None


class DiscordInteractionResponseData(BaseModel):
    content: str


class DiscordInteractionResponse(BaseModel):
    type: InteractionCallbackType
    data: DiscordInteractionResponseData
