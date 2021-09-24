from __future__ import annotations

from .imports import discord

import inspect
from enum import IntEnum


class BaseIntEnum(IntEnum):
    def __str__(self) -> str:
        return self.name

class ButtonStyles(BaseIntEnum):
    """
    A list of button styles (colors) in message components
    """
    Primary     =     	 blurple        = 1
    Secondary   =         grey          = 2
    Succes      =        green          = 3
    Danger      =         red           = 4
    url                                 = 5

    @classmethod
    def getColor(cls, s):
        if isinstance(s, int):
            return cls(s)
        if isinstance(s, cls):
            return s
        s = s.lower()
        if s in ("blurple", "primary"):
            return cls.blurple
        if s in ("grey", "gray", "secondary"):
            return cls.grey
        if s in ("green", "succes"):
            return cls.green
        if s in ("red", "danger"):
            return cls.red
class CommandType(BaseIntEnum):
    Slash       =              1
    User        =              2
    Message     =              3

    @staticmethod
    def from_string(typ):
        if isinstance(typ, str):
            if typ.lower() == "slash":
                return CommandType.Slash
            elif typ.lower() == "user":
                return CommandType.User
            elif typ.lower() == "message":
                return CommandType.Message
        elif isinstance(typ, CommandType):
            return typ
        else:
            return CommandType(typ)
    def __str__(self):
        return self.name
class ComponentType(BaseIntEnum):
    """
    A list of component types
    """
    Action_row      =           1
    Button          =           2
    Select          =           3
class OptionType(BaseIntEnum):
    """The list of possible slash command option types"""

    SUB_COMMAND             =          Subcommand           =           1
    SUB_COMMAND_GROUP       =          Subcommand_group     =           2
    STRING                  =          String               =           3
    INTEGER                 =          Integer              =           4
    BOOLEAN                 =          Boolean              =           5
    MEMBER     =   USER     =          Member               =  User =   6
    CHANNEL                 =          Channel              =           7
    ROLE                    =          Role                 =           8
    MENTIONABLE             =          Mentionable          =           9
    FLOAT                   =          Float                =          10

    @classmethod
    def any_to_type(cls, whatever) -> OptionType:
        """Converts something to a option type if possible"""
        if isinstance(whatever, int) and whatever in range(1, 11):
            return whatever
        if inspect.isclass(whatever):
            if whatever is str:
                return cls.String
            if whatever is int:
                return cls.Integer
            if whatever is bool:
                return cls.Boolean
            if whatever in [discord.User, discord.Member]:
                return cls.Member
            if whatever in [discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel]:
                return cls.Channel
            if whatever is discord.Role:
                return cls.Role
            if whatever is float:
                return cls.Float
        if isinstance(whatever, str):
            whatever = whatever.lower()
            if whatever in ["str", "string"]:
                return cls.String
            if whatever in ["int", "integer"]:
                return cls.Integer
            if whatever in ["bool", "boolean"]:
                return cls.Boolean
            if whatever in ["user", "discord.user", "member", "discord.member", "usr", "mbr"]:
                return cls.Member
            if whatever in ["channel", "textchannel", "discord.textchannel", "txtchannel"]:
                return cls.Channel
            if whatever in ["role", "discord.role"]:
                return cls.Role
            if whatever in ["mentionable", "mention"]:
                return cls.Mentionable
            if whatever in ["float", "floating", "floating number", "f"]:
                return cls.Float


class InteractionResponseType(BaseIntEnum):
    Pong                        =       1
    """respond to ping"""
    # Ack                         =       2  # deprecated
    # """``deprecated`` acknowledge that message was received"""
    # Channel_message             =       3  # deprecated
    # """``deprecated`` respond with message"""
    Channel_message             =       4
    """
    respond with message
        `command` | `component`"""
    Deferred_channel_message    =       5
    """
    defer interaction
        `command | component`"""
    Deferred_message_update     =       6
    """
    update message later
        `component`"""
    Message_update              =       7
    """
    update message for component
        `component`"""
    Autocomplete_result         =       8
    """
    respond with auto-complete choices
        `command`"""
