from __future__ import annotations

import discord

import inspect
from enum import IntEnum
from typing import Union, Callable

Channel = Union[
    discord.TextChannel, 
    discord.VoiceChannel, 
    discord.StageChannel,
    discord.StoreChannel,
    discord.CategoryChannel, 
    discord.StageChannel,
]
"""Typing object for all possible channel types, only for type hinting"""

Mentionable = Union[
    discord.abc.GuildChannel,
    discord.Member,
    discord.Role
]
"""Typing object for possible returned classes in :class:`~OptionType.Mentionable`, only for type hinting"""
# class Mentionable(
#     discord.abc.GuildChannel,
#     discord.Member,
#     discord.Role
# ):
#     def __init__(self):
#         raise NotImplemented

class BaseIntEnum(IntEnum):
    def __str__(self) -> str:
        return self.name


class ButtonStyle(BaseIntEnum):
    Blurple     =     Primary           = 1
    Grey        =     Secondary         = 2
    Green       =     Succes            = 3
    Red         =     Destructive       = 4
    URL         =     Link              = 5

    @classmethod
    def getColor(cls, s):
        if isinstance(s, int):
            return cls(s)
        if isinstance(s, cls):
            return s
        s = s.lower()
        if s in ("blurple", "primary"):
            return cls.Blurple
        if s in ("grey", "gray", "secondary"):
            return cls.Grey
        if s in ("green", "succes"):
            return cls.Green
        if s in ("red", "danger"):
            return cls.Red

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
    Action_row      =           1
    Button          =           2
    Select          =           3
class OptionType(BaseIntEnum):
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
                ret = cls.Channel
                ret.__types__ = [cls]
                return ret
            if whatever is discord.Role:
                return cls.Role
            if whatever is Mentionable:
                return cls.Mentionable
            if whatever is float:
                return cls.Float
        if isinstance(whatever, str):
            whatever = whatever.lower()
            if whatever in ["str", "string", "text", "char[]"]:
                return cls.String
            if whatever in ["int", "integer", "number"]:
                return cls.Integer
            if whatever in ["bool", "boolean"]:
                return cls.Boolean
            if whatever in ["user", "discord.user", "member", "discord.member", "usr", "mbr"]:
                return cls.Member
            if whatever in ["channel"]:
                return cls.Channel
            if whatever in ["role", "discord.role"]:
                return cls.Role
            if whatever in ["mentionable", "mention"]:
                return cls.Mentionable
            if whatever in ["float", "floating", "floating number", "f"]:
                return cls.Float
        if isinstance(whatever, list):
            ret = cls.Channel
            ret.__types__ = whatever
            return ret

    def get_channel_types(self):
        if self != self.CHANNEL or not hasattr(self, "__types__"):
            raise Exception("Bro you can't to that, its not a channel")
        types = []
        for x in self.__types__:
            if isinstance(x, discord.TextChannel):
                types.append(discord.ChannelType.text)
            if isinstance(x, discord.VoiceChannel):
                types.append(discord.ChannelType.voice)
            if isinstance(x, discord.StageChannel):
                types.append(discord.ChannelType.stage_voice)
            if isinstance(x, discord.StoreChannel):
                types.append(discord.ChannelType.store)
            if isinstance(x, discord.CategoryChannel):
                types.append(discord.ChannelType.category)
        return types
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
