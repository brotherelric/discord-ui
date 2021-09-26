from ..tools import _or, _default, _none
from ..errors import InvalidLength, WrongType
from ..enums import CommandType, OptionType
from .errors import (
    CallbackMissingContextCommandParameters, 
    MissingOptionParameter, 
    NoAsyncCallback, 
    OptionalOptionParameter
)

from ..imports import discord
from ..imports import commands

import typing
import inspect

def format_name(value):
    return str(value).lower().replace(" ", "-")

class SlashOption():
    """An option for a slash command
        
        Parameters
        ----------
        argument_type: :class:`int` | :class:`str` | :class:`class`
            What type of parameter the option should accept
        name: :class:`str`
            1-32 lowercase character name for the option
        description: :class:`str`, optional
            1-100 character description of the command; default name
        required: :class:`bool`, optional
            If the parameter is required or optional; default False
        choices: List[:class:`dict`], optional
            Choices for string and int types for the user to pick from; default None
                Choices should be formated like this: ``[{"name": "name of the choice", "value": "the real value"}, ...]``

                .. note::

                    The choice value has to be of the same type as the type this option accepts
        
        autocomplete: :class:`bool`, optional
            Whether the choices should be autogenerated, default None
        choice_generator: :class:`function`, optional
            A function that generates the choices for this option. Needds to return a list of dicts or tuples, default None
                This will automatically set autocomplete to True if autocomplete was not passed
        options: List[:class:`~SlashOption`]
            This parameter is only for subcommands to work, you shouldn't need to use that, unless you know what you're doing 
        """
    def __init__(self, argument_type, name, description=None, required=False, choices=None, autocomplete=None, choice_generator=None, options=None) -> None:
        """
        Creates a new option for a slash command

        Example
        ```py
        SlashOption(argument_type=int, name="Your number", required=True, choices=[{"name": "a cool number", "value": 2}])
        ```
        """
        autocomplete = autocomplete or choice_generator is not None

        self.__choice_generators__ = {}

        self._json = {}
        self.argument_type = argument_type
        self.name = name
        self.description = _or(description, self.name)
        self.required = required
        self.options = _default([], options)
        self.autocomplete = autocomplete
        self.choices = choices if self.autocomplete is False else None
        self.choice_generator: typing.Callable[[typing.Any], typing.List[typing.Union[dict, tuple]]] = choice_generator
        """A function which will generate choices for this option"""
    def __repr__(self) -> str:
        return f"<discord_ui.SlashOption({str(self.to_dict())})>"
    def __eq__(self, o: object) -> bool:
        if isinstance(o, SlashOption):
            return (
                self.argument_type == o.argument_type 
                    and 
                self.name == o.name 
                    and 
                self.description == o.description 
                    and 
                self.required == o.required 
                    and 
                self.choices == o.choices 
                    and 
                self.options == o.options
            )
        elif isinstance(o, dict):
            return (
                self.argument_type == o["type"] 
                    and 
                self.name == o["name"] 
                    and 
                self.description == o.get("description") 
                    and 
                self.required == o.get("required", False)
                    and 
                (self.choices == o.get("choices", []) or self.choices == o.get("choices", None))
                    and 
                (self.options == o.get("options", []) or self.options == o.get("options", None))
                    and
                self.autocomplete == o.get("autocomplete", False)
            )
        return False
    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    @property
    def argument_type(self) -> int:
        """Parameter type that the option accepts
        
        :type: :class:`int`
        """
        return OptionType(self._json["type"])
    @argument_type.setter
    def argument_type(self, value):
        self._json["type"] = getattr(value, "value", OptionType.any_to_type(value))

    @property
    def name(self) -> str:
        """The name of the option appearing in discord
        
        :type: :class:`str`
        """
        return self._json["name"]
    @name.setter
    def name(self, value):
        if len(value) > 32 or len(value) < 1:
            raise InvalidLength("name", 1, 32)
        self._json["name"] = value.lower().replace(" ", "_")

    @property
    def description(self) -> str:
        """The description of the option appearing under the name
        
        :type: :class:`str`
        """
        return self._json["description"]
    @description.setter
    def description(self, value):
        if len(value) > 100 or len(value) < 1:
            raise InvalidLength("description", 1, 100)
        self._json["description"] = value

    @property
    def required(self) -> bool:
        """Whether this parameter is required to use or not

        :type: :class:`bool`
        """
        return self._json.get("required", False)
    @required.setter
    def required(self, value):
        if not isinstance(value, bool):
            raise WrongType("required", value, "bool") 
        self._json["required"] = value

    @property
    def choices(self) -> typing.List[dict]:
        """Choices for string and int types for the user to pick from
        
        .. note::
    
            Choices are formated like this: ``[{"name": "name of the choice", "value": "the real value"}, ...]``
    
        :type: List[:class:`dict`]
        """
        return self._json.get("choices")
    @choices.setter
    def choices(self, value):
        if isinstance(value, list):
            if all(isinstance(x, dict) for x in value):
                self._json["choices"] = value
            elif all(isinstance(x, tuple) for x in value):
                self._json["choices"] = [{"name": x[0], "value": x[1]} for x in value]
            else:
                raise WrongType("choices", value, ["List[dict]", "List[tuple]"])

    @property
    def options(self) -> typing.List['SlashOption']:
        """The parameters for the command

        :type: List[:class:`~SlashOptions`]
        """
        return [SlashOption._from_data(x, self.__choice_generators__.get(x["name"])) for x in self._json.get("options", [])]
    @options.setter
    def options(self, options):
        if not isinstance(options, list):
            raise WrongType("options", options, "list")
        if all(isinstance(x, (SlashOption, dict)) for x in options):
            self._json["options"] = [(x.to_dict() if type(x) is SlashOption else x) for x in options]
        else:
            i = 0
            for x in options:
                if not isinstance(x, SlashOption) and not isinstance(x, dict):
                    raise WrongType("options[" + str(i) + "]", x, ["dict", "SlashOption"])
                i += 1
        self.__choice_generators__ = {x.name: x.choice_generator or self.__choice_generators__.get(x.name) for x in [SlashOption._from_data(o) if isinstance(o, dict) else o for o in options]}

    @property
    def autocomplete(self) -> bool:
        """Whether the choices for this option should be autocompleted
        
        type: :class:`bool`
        """
        return self._json.get("autocomplete", False)
    @autocomplete.setter
    def autocomplete(self, value):
        self._json["autocomplete"] = value

    @property
    def focused(self) -> bool:
        return self._json.get("focused", False)
    
    @staticmethod
    def _from_data(data: dict, generator=None):
        return SlashOption(data["type"], data["name"], data["description"], data.get("required", False), data.get("choices"), data.get("autocomplete", False), generator, data.get("options"), )

    def to_dict(self):
        return self._json

class AdditionalType:
    MESSAGE     =       44
    GUILD       =       45

class SlashPermission():
    """Permissions for a slash commannd
        
        Parameters
        ----------
            allowed: :class:`dict` | List[:class:`discord.Member` | :class:`discord.User` | :class:`discord.Role`], optional
                A list of ids, users or members that can use the command; default None
                    Format: ``{"role_or_user_id": permission_type}]``


            forbidden: :class:`dict` | List[:class:`discord.Member` | :class:`discord.User` | :class:`discord.Role`], optional
                A list of ids, users or members that are forbidden to use the command; default None
        

            .. note::

                If you want to use a role id, the permission type has to be 1, and if you want to specify a user id, it has to be 2

                You can use ``SlashPermission.ROLE`` and ``SlashPermission.USER`` instead

        """
    def __init__(self, allowed: dict=None, forbidden=None) -> None:
        """Creates a new permission object for a slash command
        
        Example
        ```py
        SlashPermission(allowed=[
                await bot.fetch_user(bot.owner_id)
            ], forbidden={
                539459006847255232: SlashPermission.User,
                874357255829606402: SlashPermission.Role
            }
        )
        ```
        """
        
        self._json = []
        if allowed is not None:
            if isinstance(allowed, dict):
                for _id, _type in allowed.items():
                    self._json.append(
                        {
                            "id": int(_id),
                            "type": _type,
                            "permission": True
                        }
                    )
            elif isinstance(allowed, list):
                for t in allowed:
                    self._json.append({
                        "id": t.id,
                        "type": SlashPermission.USER if isinstance(t, (discord.User, discord.Member)) else SlashPermission.ROLE,
                        "permission": True
                    })
        if forbidden is not None:
            if isinstance(forbidden, dict):
                for _id, _type in forbidden.items():
                    self._json.append(
                        {
                            "id": int(_id),
                            "type": _type,
                            "permission": False
                        }
                    )
            elif isinstance(forbidden, list):
                for t in forbidden:
                    self._json.append({
                        "id": t.id,
                        "type": SlashPermission.USER if type(t) in [discord.User, discord.Member] else SlashPermission.ROLE,
                        "permission": False
                    })
            else:
                raise WrongType("forbidden", forbidden, ["Dict[int | str, int]", "List[discord.Member | discord.User | discord.Role]"])

    @classmethod
    def Empty(cls) -> 'SlashPermission':
        """Returns an empty permission for the command"""
        return cls()
    def to_dict(self):
        return self._json
    def __eq__(self, o: object) -> bool:
        if isinstance(o, SlashPermission):
            return (
                len(self.allowed) == len(o.allowed) and all(self.allowed[i] == o.allowed[i] for i, _ in enumerate(o.allowed)) and
                len(self.forbidden) == len(o.forbidden) and all(self.forbidden[i] == o.forbidden for i, _ in enumerate(o.forbidden))
            )
        elif isinstance(o, dict):
            o_allowed = [x for x in o["permissions"] if x["permission"] == True]
            o_forbidden = [x for x in o["permissions"] if x["permission"] == False]

            return (
                len(self.allowed) == len(o_allowed) and all(self.allowed[i] == o_allowed[i] for i, _ in enumerate(self.allowed)) and
                len(self.forbidden) == len(o_forbidden) and all(self.forbidden[i] == o_forbidden[i] for i, _ in enumerate(self.forbidden))
            )
        return False
    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)
    def __repr__(self) -> str:
        return f"<discord_ui.SlashPermission({self.to_dict()})>"

    ROLE        =       Role      =   1
    USER        =       User      =   2

    @property
    def allowed(self) -> dict:
        return [x for x in self._json if x["permission"] == True]
    @property
    def forbidden(self) -> dict:
        return [x for x in self._json if x["permission"] == False]


class BaseCommand():
    __slots__ = ('__aliases__', '__sync__', '__original_name__', '__auto_defer__')
    def __init__(self, command_type, callback, name=None, description=None, options=None, guild_ids=None, default_permission=None, guild_permissions=None) -> None:
        self.__aliases__ = getattr(callback, "__aliases__", None)
        self.__sync__ = getattr(callback, "__sync__", True)
        self.__auto_defer__ = getattr(callback, "__auto_defer__", None)
        self.__guild_changes__ = getattr(callback, "__guild_changes__", {})
        self.__choice_generators__ = {}

        self._json = {"type": getattr(command_type, "value", command_type)}

        self.options = _default([], options)
        if callback is not None:
            if not inspect.iscoroutinefunction(callback):
                raise NoAsyncCallback()

            callback_params = inspect.signature(callback).parameters
            if self.options is not None:
                for op in self.options:
                    if callback_params.get(op.name) is None:
                        raise MissingOptionParameter(op.name)
                    param = callback_params[op.name]
                    if not op.required and param.default is param.empty:
                        raise OptionalOptionParameter(param.name)
            if self.options in [[], None] and self.command_type is CommandType.Slash:
                _ops = []
                has_self = False
                for _i, _name in enumerate(callback_params):
                    # ignore context parameter
                    if _name == "self":
                        has_self = True
                        continue
                    if _i == (1 if has_self else 0):
                        continue
                    _val = callback_params.get(_name)
                    op_type = None
                    if _val.annotation != _val.empty:
                        op_type = _val.annotation
                    elif _val.default != inspect._empty:
                        op_type = type(_val.default)
                    else: 
                        op_type = _name
                    if OptionType.any_to_type(op_type) is None:
                        raise InvalidArgument("Could not find a matching option type for parameter '" + str(op_type) + "'")
                    _ops.append(SlashOption(op_type, _name, required=_val.default == inspect._empty))
                self.options = _ops

        self.callback: function = callback
        self.name: str = _or(name, self.callback.__name__ if not _none(self.callback) else None)
        # Set the original name to the name once so if the name should be changed, this value still stays to what it is
        self.__original_name__ = self.name
        self.description: str = _or(description, inspect.getdoc(callback).split("\n")[0] if not _none(callback) and inspect.getdoc(callback) is not None else None, self.name)
        if default_permission is None:
            default_permission = True
        self.default_permission = default_permission
        if not _none(guild_permissions):
            for _id, perm in list(guild_permissions.items()):
                if not isinstance(_id, (str, int, discord.User, discord.Member, discord.Role)):
                    raise WrongType("guild_permissions key " + str(_id), _id, ["str", "int", "discord.User", "discord.Member", "discord.Role"])
                if not isinstance(perm, SlashPermission):
                    raise WrongType("guild_permission[" + ("'" if isinstance(_id, str) else "") + str(_id) + ("'" if isinstance(_id, str) else "") + "]", perm, "SlashPermission")
        
        self.guild_permissions: typing.Dict[(typing.Union[str, int], SlashPermission)] = guild_permissions
        self.permissions: SlashPermission = SlashPermission()
        self.guild_ids: typing.List[int] = _default(None, [int(x) for x in _or(guild_ids, [])])
        """The ids of the guilds where the command is available"""
    def __str__(self) -> str:
        return str(self.to_dict())
    def __eq__(self, o: object) -> bool:
        if isinstance(o, dict):
            return (
                o.get('type') == self.command_type.value 
                and o.get('name') == self.name
                and o.get('description') == self.description
                and o.get('options', []) == self.options
                and o.get("default_permission", True) == self.default_permission
            )
        elif isinstance(o, SlashCommand):
            return (
                o._json('type') == self._json["type"]
                and o.name == self.name
                and o.description == self.description
                and o.options == self.options
                and o.default_permission == self.default_permission
            )
        else:
            return False
    def __ne__(self, o: object) -> bool:
        return not self.__eq__(o)

    @property
    def is_message_context(self) -> bool:
        """Wether is command is a message-context command"""
        return self.command_type is CommandType.Message
    @property
    def is_user_context(self) -> bool:
        """Whether this command is a user-context command"""
        return self.command_type is CommandType.User
    @property
    def is_chat_input(self) -> bool:
        """Whether this command is a chat-input command"""
        return self.command_type is CommandType.Slash
    @property
    def is_slash_command(self) -> bool:
        """
        Whether this command is a slashcommand
            Same as `.is_chat_input`
        """
        return self.is_chat_input
    
    @property
    def original_name(self) -> str:
        """The original name for this command"""
        return self.__original_name__
    @property
    def aliases(self) -> typing.List[str]:
        """The list of available aliases for this command"""
        return self.__aliases__
    @property
    def has_aliases(self) -> bool:
        """Returns True if this command has aliases"""
        return hasattr(self, "__aliases__") and self.__aliases__ is not None
    @property
    def is_alias(self) -> bool:
        """Returns True if this command is an alias to another command"""
        return self.__aliases__ is not None and self.name in self.__aliases__

    # region command
    @property
    def command_type(self) -> CommandType:
        return CommandType(self._json["type"])

    @property
    def name(self) -> str:
        """The name of the slash command
        
        :type: :class:`str`
        """
        return self._json["name"]
    @name.setter
    def name(self, value):
        if _none(value):
            raise InvalidArgument("You have to specify a name")
        if not isinstance(value, str):
            raise WrongType("name", value, "str")
        if len(value) > 32 or len(value) < 1:
            raise InvalidLength("name", 1, 32)
        if self.command_type is CommandType.Slash:
            self._json["name"] = format_name(value)
        else:
            self._json["name"] = value
    @property
    def description(self) -> str:
        """The description of the command
        
        :type: :class:`str`
        """
        return self._json['description']
    @description.setter
    def description(self, value):
        if not isinstance(value, str):
            raise WrongType("description", value, "str")
        if len(value) > 100 or len(value) < 1:
            raise InvalidLength("description", 1, 100)
        self._json["description"] = value
    @property
    def options(self) -> typing.List['SlashOption']:
        """The parameters for the command
        
        :type: List[:class:`~SlashOption`]
        """
        return [SlashOption._from_data(x, self.__choice_generators__.get(x["name"])) for x in self._json.get("options", [])]
    @options.setter
    def options(self, options):
        if not isinstance(options, list):
            raise WrongType("options", options, "list")
        if all(isinstance(x, (SlashOption, dict)) for x in options):
            self._json["options"] = [(x.to_dict() if isinstance(x, SlashOption) else x) for x in options]
        else:
            i = 0
            for x in options:
                if not isinstance(x, (SlashOption, dict)):
                    raise WrongType("options[" + str(i) + "]", x, ["dict", "SlashOption"])
                i += 1
        self.__choice_generators__ = {x.name: x.choice_generator or self.__choice_generators__.get(x.name) for x in [SlashOption._from_data(o) if isinstance(o, dict) else o for o in options]}
    # endregion
    # region permissions
    @property
    def default_permission(self) -> typing.Union[str, bool]:
        """Default permissions that a user needs to have in order to execute this command
            If a bool was used, it will indicate whether this command can be used by everyone
        
        :type: :class:`str` | :class:`bool`
        """
        raw = self._json.get("default_permission", False)
        if isinstance(raw, str):
            return discord.Permissions(int(raw))
        return raw
    @default_permission.setter
    def default_permission(self, value):
        self._json["default_permission"] = str(value.value) if isinstance(value, discord.Permissions) else value
    # endregion

    def _patch(self, command):
        self.__aliases__ = command.__aliases__
        self.guild_permissions = command.guild_permissions

    def copy(self):
        """Copies itself into a new object"""
        raise NotImplementedError()

    def to_dict(self):
        return self._json

class SlashCommand(BaseCommand):
    """A basic slash command
        
        Parameters
        ----------
            callback: :class:`function`
                The callback function
            name: :class:`str`
                1-32 characters long name
                    If name is not passed, the name of the callback function will be used; default None
                    
                .. important::

                    The name will be corrected automaticaly (spaces will be replaced with "-" and the name will be lowercased)

            description: :class:`str`, optional
                1-100 character description of the command; default None
                    If description is not passed, the docstring description of the callback function is used. 
                    If no docstring exists, the name of the command will be used
            options: List[:class:`~SlashOptions`], optional
                Parameters for the command; default None
            choices: List[:class:`tuple`] | List[:class:`dict`], optional
                Choices for string and int types for the user to pick from; default None
            guild_ids: :class:`str` | :class:`int`, optional
                A list of guild ids where the command is available; default None
            default_permission: :class:`bool` | :class:`discord.Permissions`, optional
                Permissions that a user needs to have in order to execute the command, default ``True``. 
                    If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
            guild_permissions: Dict[``guild_id``: :class:`~SlashPermission`]
                The permissions for the command in guilds
                    Format: ``{"guild_id": SlashPermission}``


    """
    def __init__(self, callback, name=None, description=None, options=None, guild_ids=None, default_permission=None, guild_permissions=None) -> None:
        """
        Creates a new base slash command
        
        Example

        ```py
        async def my_function(command, parameter=None):
            pass

        SlashCommand(callback=my_function, name="hello_world", description="This is a test command",
            options=[
                SlashOption(str, name="parameter", description="this is a parameter", choices=[("choice 1", 1)])
            ], guild_ids=[785567635802816595], default_permission=False,
            guild_permissions={
                785567635802816595: SlashPermission(allowed={"539459006847254542": SlashPermission.USER})
            })
        ```
        """
        BaseCommand.__init__(self, CommandType.Slash, callback, name, description, options, guild_ids, default_permission, guild_permissions)
    def copy(self) -> 'SlashCommand':
        c = SlashCommand(self.callback, self.name, self.description, self.options, self.guild_ids, self.default_permission, self.guild_permissions)
        for x in self.__slots__:
            setattr(c, x, getattr(self, x))
        return c

class SlashSubcommand(BaseCommand):
    def __init__(self, callback, base_names, name, description=None, options=[], guild_ids=None, default_permission=None, guild_permissions=None) -> None:
        if isinstance(base_names, str):
            base_names = [base_names]
        if len(base_names) > 2:
            raise InvalidArgument("subcommand groups are currently limited to 2 bases")
        if any([len(x) > 32 or len(x) < 1 for x in base_names]):
            raise InvalidLength("base_names", 1, 32)
        BaseCommand.__init__(self, CommandType.Slash, callback, name, description, options, guild_ids=guild_ids, default_permission=default_permission, guild_permissions=guild_permissions)
        self.base_names = [format_name(x) for x in base_names]
    
    def to_option(self) -> SlashOption:
        return SlashOption(OptionType.SUB_COMMAND, self.name, self.description, options=self.options or None, required=False)
    def to_dict(self):
        return self.to_option().to_dict()
    def copy(self):
        c = SlashSubcommand(self.callback, self.base_names, self.name, self.description, self.options, self.guild_ids, self.default_permission, self.guild_permissions)
        for x in self.__slots__:
            setattr(c, x, getattr(self, x))
        return c

class ContextCommand(BaseCommand):
    def __init__(self, context_type, callback, name=None, guild_ids=None, default_permission = True, guild_permissions = None) -> None:
        if callback is not None:
            callback_params = inspect.signature(callback).parameters
            if len(callback_params) < 2:
                raise CallbackMissingContextCommandParameters()
        BaseCommand.__init__(self, context_type, callback, name=name, guild_ids=guild_ids, default_permission=default_permission, guild_permissions=guild_permissions)

    @property
    def description(self) -> str:
        return ""
    @description.setter
    def description(self, value):
        pass
    @property
    def options(self) -> list:
        return []
    @options.setter
    def options(self, value):
        pass

class UserCommand(ContextCommand):
    def __init__(self, callback, name=None, guild_ids = None, default_permission = True, guild_permissions = None) -> None:
        ContextCommand.__init__(self, CommandType.User, callback, name, guild_ids, default_permission, guild_permissions)
    def copy(self) -> 'UserCommand':
        c = UserCommand(self.callback, self.name, self.guild_ids, self.default_permission, self.guild_permissions)
        for x in self.__slots__:
            setattr(c, x, getattr(self, x))
        return c

class MessageCommand(ContextCommand):
    def __init__(self, callback, name=None, guild_ids = None, default_permission = True, guild_permissions = None) -> None:
        ContextCommand.__init__(self, CommandType.Message, callback, name, guild_ids, default_permission, guild_permissions)
    def copy(self) -> 'MessageCommand':
        c = MessageCommand(self.callback, self.name, self.guild_ids, self.default_permission, self.guild_permissions)
        for x in self.__slots__:
            setattr(c, x, getattr(self, x))
        return c