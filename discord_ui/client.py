from .cogs import BaseCallable, CogCommand, CogSubCommandGroup, InteractionableCog, ListeningComponent
from .http import get_message_payload, BetterRoute, send_files
from .tools import MISSING, EMPTY_CHECK, _none, _or, get_index, setup_logger, get
from .errors import MissingListenedComponentParameters, WrongType
from .components import Button, Component, SelectMenu

from .slash.http import SlashHTTP
from .slash.errors import NoAsyncCallback
from .slash.tools import ParseMethod, handle_options, handle_thing
from .slash.types import (
    CommandCache, OptionType, SlashOption,
    MessageCommand , SlashCommand, SlashSubcommand, UserCommand
)

from .receive import (
    ChoiceGeneratorContext, ComponentContext, 
    Interaction, InteractionType,
    PressedButton, SelectedMenu,
    SlashInteraction, SubSlashInteraction, ContextInteraction,
    getMessage, Message
)
from .listener import Listener
from .override import override_dpy as override_it
from .enums import CommandType, InteractionResponseType, ComponentType

from .override import override_dpy as override_it
from .listener import Listener
from .enums import InteractionResponseType, ComponentType


import discord
from discord.errors import *
from discord.ext import commands

import json
import inspect
import asyncio
import contextlib
from typing import Any, Callable, Coroutine, Dict, List, Tuple, Union, TypeVar
try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

logging = setup_logger(__name__)

__all__ = (
    'UI',
    'Slash',
    'Components',
)

# Command Type
_C = TypeVar("_C")

class Slash():
    """
    A class for using slash commands
    
    Parameters
    ----------
    client: :class:`commands.Bot`
        The bot client

    parse_method: :class:`bool`, optional
        How received option data should be treated; Default ``ParseMethod.AUTO``

    delete_unused: :class:`bool`, optional
        Whether the commands that are not registered by this slash extension should be deleted in the api; Default ``False``

    sync_on_cog: :class:`bool`, optional
        Whether the slashcommands should be updated whenever a new cog is added or removed; Default ``False``

    wait_sync: :class:`float`, optional
        How many seconds will be waited until the commands are going to be synchronized; Default ``1``

    auto_defer: Tuple[:class:`bool`, :class:`bool`]
        Settings for the auto-defer; Default ``(True, False)``

        ``[0]``: Whether interactions should be deferred automatically

        ``[1]``: Whether the deferration should be hidden (True) or public (False)

    Example
    ------------------
    Example for using slash commands

    .. code-block::

        ...
        # Your bot declaration and everything
        slash = Slash(client)

    For creating a slash command use

    .. code-block::

        ...
        @slash.command(name="my_command", description="this is my slash command", options=[SlashOption(str, "option", "this is an option")])
        async def command(ctx: SlashInteraction):
            ...
    
    And for subcommand groups use

    .. code-block::

        ...
        @slash.subcommand_group(base_names=["base", "group"], name="sub", description="this is a sub command group")
        async def subgroup(ctx: SubSlashInteraction):
            ...
        

    """
    def __init__(self, client, parse_method = ParseMethod.AUTO, auto_sync=True, delete_unused = False, sync_on_cog=False, wait_sync = 1, auto_defer = False) -> None:
        """
        Creates a new slash command thing
        
        Example
        ```py
        Slash(client)
        ```
        """
        self.ready = False
        self.parse_method: int = parse_method
        self.delete_unused: bool = delete_unused
        self.wait_sync: float = wait_sync
        self.auto_defer: Tuple[bool, bool] = (auto_defer, False) if isinstance(auto_defer, bool) else auto_defer
        self.auto_sync = auto_sync

        self._discord: commands.Bot = client
        self.http: SlashHTTP = None # set it when bot is connected
        self._discord._connection.slash_http = None # set when bot is connected
        self.commands = CommandCache(self._discord)
        
        if discord.__version__.startswith("2"):
            self._discord.add_listener(self._on_slash_response, "on_socket_raw_receive")
        elif discord.__version__.startswith("1"):
            self._discord.add_listener(self._on_slash_response, 'on_socket_response')

        old_add = self._discord.add_cog
        def add_cog_override(*args, **kwargs):
            cog = args[0] if len(args) > 0 else kwargs.get("cog")
            if not isinstance(cog, InteractionableCog):
                # adding attributees to cog form InteractionableCog
                for s in InteractionableCog.__custom_slots__:
                    setattr(cog, "s", getattr(InteractionableCog, s))
            for com in self._get_cog_commands(cog):
                com.cog = cog
                self._add_to_cache(com)
            old_add(*args, **kwargs)
            if self.ready is True and sync_on_cog is True:
                self._discord.loop.create_task(self.sync_commands(self.delete_unused))
        self._discord.add_cog = add_cog_override

        old_remove = self._discord.remove_cog
        def remove_cog_override(*args, **kwargs):
            cog = args[0] if len(args) > 0 else kwargs.get("cog")
            for com in self._get_cog_commands(cog):
                com.cog = cog
                self.commands.remove(com)
            old_remove(*args, **kwargs)
            if self.ready is True and sync_on_cog is True:
                self._discord.loop.create_task(self.sync_commands(self.delete_unused))
        self._discord.remove_cog = remove_cog_override
        
        async def on_connect():
            self.http = SlashHTTP(self._discord)
            self._discord._connection.slash_http = self.http
            self.ready = True
            if self.auto_sync is False:
                return
            await asyncio.sleep(_or(self.wait_sync, 1))
            await self.commands.sync(self.delete_unused)
            # await self.sync_commands(self.delete_unused)
        self._discord.add_listener(on_connect)

    async def _on_slash_response(self, msg):
        if discord.__version__.startswith("2"):
            if isinstance(msg, bytes):
                raise NotImplementedError("decompressing was removed! Please upgrade your discord.py version")
            if isinstance(msg, str):
                msg = json.loads(msg)
        if msg["t"] != "INTERACTION_CREATE":
            return
        data = msg["d"]

        # filter out any interaction that is not a application command interaction
        if int(data["type"]) not in [InteractionType.PING, InteractionType.APPLICATION_COMMAND, InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE]:
            return

        # get the author
        user = discord.Member(data=data["member"], guild=self._discord._connection._get_guild(int(data["guild_id"])), state=self._discord._connection) if data.get("member") is not None else discord.User(state=self._discord._connection, data=data["user"])
        # as stated in https://github.com/discord-py-ui/discord-ui/issues/94, .author.send won't work because if no dm_channel was opened for the user 
        if user.dm_channel is None:
            await user.create_dm()

        # things for autocomplete
        if int(data["type"]) == InteractionType.APPLICATION_COMMAND_AUTOCOMPLETE:
            raw_options = {}
            """The options that were already selected"""
            command = None
            """The original command"""
            # if command is not slash command (this cenario is not possible, but you never know)
            if CommandType(data["data"]["type"]) is not CommandType.Slash:
                return
            command = self.commands.get_command_for(data)
            # if the command is not a subcommand
            if not (data["data"].get("options") and data["data"]["options"][0]["type"] in [OptionType.SUB_COMMAND, OptionType.SUB_COMMAND_GROUP]):
                raw_options = []
                if data["data"].get("options") is not None:
                    options = await handle_options(data, data["data"]["options"], self.parse_method, self._discord)
                    raw_options = data["data"]["options"]
            # if command is a subcommand
            else:
                if command:
                    op = data["data"]["options"][0]
                    while op["type"] != 1:
                        op = op["options"][0]
                    fixed_options = op.get("options", [])
                    raw_options = fixed_options
                    options = await handle_options(data, fixed_options, self.parse_method, self._discord)

            if command is None:
                logging.warning("no slashcommand handler found for " + data["data"]["name"])
                return
            
            parsed_options = {
                x["name"]: {
                    "name": x["name"], 
                    "value": await handle_thing(
                            x["value"], x["type"], data, self.parse_method, self._discord
                    )
                } | (
                    {"focused": True} if x.get("focused") else {}
                ) 
                for x in raw_options
            }
            choice_ctx = ChoiceGeneratorContext(command, self._discord._connection, data, parsed_options, user) 
            return await self.http.respond_to(choice_ctx.id, choice_ctx.token, InteractionResponseType.Autocomplete_result, {
                "choices": [(
                        {"name": x[0], "value": x[1]} if isinstance(x, tuple) else x
                    ) for x in (await get(command.options, choice_ctx.focused_option["name"], lambda x: getattr(x, "name", None)).choice_generator(choice_ctx))
                ]
            })

        interaction = Interaction(self._discord._connection, data, user)
        if self.auto_defer[0] is True:
            await interaction.defer(self.auto_defer[1])
        self._discord.dispatch("interaction_received", interaction)


        command = self.commands.get_command_for(data)
        
        # region basic-commands
        # slash command
        if CommandType(data["data"]["type"]) is CommandType.Slash and not (data["data"].get("options") and data["data"]["options"][0]["type"] in [OptionType.SUB_COMMAND, OptionType.SUB_COMMAND_GROUP]):
            if command is not None:
                options = {}
                if data["data"].get("options") is not None:
                    options = await handle_options(data, data["data"]["options"], self.parse_method, self._discord)
                context = SlashInteraction(self._discord, command=command, data=data, user=user, args=options)
                # Handle autodefer
                context._handle_auto_defer(self.auto_defer)
                self._discord.dispatch("slash_command", context)
                if hasattr(command, "invoke"):
                    await command.invoke(context, **options)
                elif command.callback is not None:
                    await command.callback(context, **options)
                return
        # UserContext command
        elif CommandType(data["data"]["type"]) is CommandType.User:
            if command is not None:
                member = await handle_thing(data["data"]["target_id"], OptionType.MEMBER, data, self.parse_method, self._discord)
                context = ContextInteraction(self._discord, command=command, data=data, user=user, param=member)
                # Handle autodefer
                context._handle_auto_defer(self.auto_defer)

                self._discord.dispatch("context_command", context, member)
                if command.callback is not None:
                    if hasattr(command, "invoke"):
                        await command.invoke(context, member)
                    else:
                        await command.callback(context, member)
                return
        # MessageContext command
        elif CommandType(data["data"]["type"]) is CommandType.Message:
            if command is not None:
                message = await handle_thing(data["data"]["target_id"], 44, data, self.parse_method, self._discord)
                context = ContextInteraction(self._discord, command=command, data=data, user=user, param=message)
                # Handle autodefer
                context._handle_auto_defer(self.auto_defer)
                
                self._discord.dispatch("context_command", context, message)
                if command.callback is not None:
                    if hasattr(command, "invoke"):
                        await command.invoke(context, message)
                    else:
                        await command.callback(context, message)
                return
        #endregion

        # subcommands
        fixed_options = []
        if command:
            op = data["data"]["options"][0]
            while op["type"] != 1:
                op = op["options"][0]
            fixed_options = op.get("options", [])
            options = await handle_options(data, fixed_options, self.parse_method, self._discord)

            context = SubSlashInteraction(self._discord, command, data, user, options)
            # Handle auto_defer
            context._handle_auto_defer(self.auto_defer)

            self._discord.dispatch("slash_command", context)
            if hasattr(command, "invoke"):
                await command.invoke(context, **options)
            elif command.callback is not None:
                await command.callback(context, **options)
            return


    def _get_cog_commands(self, cog):
        # Get all BaseCallables flagged with __type__ of 1 (command)
        return [x[1] for x in inspect.getmembers(cog, lambda x: isinstance(x, BaseCallable) and x.__type__ == 1)]
    async def _get_guild_api_command(self, name, typ, guild_id) -> Union[dict, None]:
        # returns all commands in a guild
        for x in await self._get_guild_commands(guild_id):
            if hasattr(typ, "value"):
                typ = typ.value
            if x["name"] == name and x["type"] == typ:
                return x
    async def _get_global_api_command(self, name, typ) -> Union[dict, None]:
        for x in await self._get_global_commands():
            if x["name"] == name and x["type"] == typ:
                return x

    async def _get_commands(self) -> List[dict]:
        return await self._get_global_commands() + await self._get_all_guild_commands()
    async def _get_global_commands(self) -> List[dict]:
        return await self.http.get_global_commands()
    async def _get_all_guild_commands(self):
        commands = []
        async for x in self._discord.fetch_guilds():
            try:
                commands += await self.http.get_guild_commands(x.id)
            except Forbidden:
                logging.warn("Got forbidden in " + str(x.name) + " (" + str(x.id) + ")")
                continue
        return commands
    async def _get_guild_commands(self, guild_id: str) -> List[dict]:
        logging.debug("getting guild commands in " + str(guild_id))
        return await self.http.get_guild_commands(guild_id)
    
    def gather_commands(self) -> Dict[str, SlashCommand]:
        commands = self.commands.copy()
        for _base in self.subcommands:
            bbase_exists = commands.get(_base) is not None
            # baase for the subcommands
            basic_base = commands.get(_base) or SlashCommand(None, _base)
            # get first base
            for _sub in self.subcommands[_base]:
                # get second base/command
                sub = self.subcommands[_base][_sub]
                # when command has subcommand groups
                if isinstance(sub, dict):
                    for _group in self.subcommands[_base][_sub]:
                        # the subcommand group
                        group = self.subcommands[_base][_sub][_group]
                        if not bbase_exists:    
                            basic_base.guild_permissions = group.guild_permissions
                            basic_base.guild_ids = group.guild_ids
                            group._base = basic_base
                        # if there's already a base command
                        if commands.get(_base) is not None:
                            # Check if base already has an option with the subs name
                            index = get_index(commands[_base].options, _sub, lambda x: getattr(x, "name"))
                            # if first base_name already exists
                            if index > -1:
                                # add to sub options
                                base_ops = commands[_base].options
                                base_ops[index].options += [group.to_option()]
                                commands[_base].options = base_ops
                            # if not exists
                            else:
                                # create sub option + group option
                                commands[_base].options += [SlashOption(OptionType.SUB_COMMAND_GROUP, _sub, options=[group.to_option()])]
                        # if no base command
                        else:
                            commands[_base] = SlashCommand(None, _base, None, [
                                        SlashOption(OptionType.SUB_COMMAND_GROUP, _sub, options=[group.to_option()])
                                ], guild_ids=group.guild_ids, default_permission=group.default_permission, guild_permissions=group.guild_permissions
                            )
                # if is basic subcommand
                else:
                    if not bbase_exists:    
                        basic_base.guild_permissions = sub.guild_permissions
                        basic_base.guild_ids = sub.guild_ids
                    sub._base = basic_base
                    # If base exists
                    if commands.get(_base) is not None:
                        commands[_base].options += [sub.to_option()]
                    # if no base exsists in commands
                    else:
                        # create base0 command with name option
                        commands[_base] = SlashCommand(None, _base, options=[sub.to_dict()], guild_ids=sub.guild_ids, default_permission=sub.default_permission, guild_permissions=sub.guild_permissions)
        return commands

    async def create_command(self, command) -> SlashCommand:
        """
        Adds a command to the api. You shouldn't use this method unless you know what you're doing
        
        Parameters
        ----------
        command: :class:`SlashCommand` | :class:`ContextCommand`
            The command that should be added

        """
        if command.guild_ids is not None:
            guild_ids = command.guild_ids
            own_guild_ids = [x.id for x in self._discord.guilds]
            for x in guild_ids:
                if command.guild_permissions is not None:
                    for x in list(command.guild_permissions.keys()):
                        if int(x) not in own_guild_ids:
                            logging.error(f"Skipping guild {x}, because client is not in this guild")
                            continue
                if int(x) not in own_guild_ids:
                    logging.error("SKipping guild, because client is not in a server with the id '" + str(x) + "'")

                if command.guild_permissions is not None:
                    command.permissions = command.guild_permissions.get(x)
                
                await self.add_guild_command(command, x)
        else:
            await self.add_global_command(command)
        return command
    async def add_global_command(self, base):
        """
        Adds a slash command to the global bot commands
        
        Parameters
        ----------
        base: :class:`~SlashCommand`
            The slash command to add
        
        """
        api_command = await self._get_global_api_command(base.name, base._json["type"])
        if api_command is None:
            await self.http.create_global_command(base.to_dict())
        else:
            if api_command != base:
                await self.http.edit_global_command(api_command["id"], base.to_dict())
    async def add_guild_command(self, base, guild_id):
        """
        Adds a slash command to a guild
        
        Parameters
        ----------
        base: :class:`~SlashCommand`
            The guild slash command which should be added
        guild_id: :class:`str`
            The ID of the guild where the command is going to be added
        
        """

        target_guild = guild_id
        api_command = await self._get_guild_api_command(base.name, base.command_type, guild_id)
        if api_command is not None:
            api_permissions = await self.http.get_command_permissions(api_command["id"], guild_id)
        global_command = await self._get_global_api_command(base.name, base.command_type)
        # If no command in that guild or a global one was found
        if api_command is None or global_command is not None:
            # # Check global commands
            # If global command exists, it will be deleted
            if global_command is not None:
                await self.http.delete_global_command(global_command["id"])
            await self.http.create_guild_command(base.to_dict(), target_guild, base.permissions.to_dict())
        elif api_command != base:
            await self.http.edit_guild_command(api_command["id"], target_guild, base.to_dict(), base.permissions.to_dict())
        elif api_permissions != base.permissions:
            await self.http.update_command_permissions(guild_id, api_command["id"], base.permissions.to_dict())

    async def update_permissions(self, name, typ: Literal["slash", 1, "user", 2, "message", 3] = 1, *, guild_id=None, default_permission=None,  permissions=None, global_command=False):
        """
        Updates the permissions for a command
        
        Parameters
        ----------
        name: :class:`str`
            The name of the command that should be updated
        typ: :class:`str` | :class:`int`
            The type of the command (one of ``"slash", CommandType.Slash, "user", CommandType.User, "message", CommandType.Message``)
        default_permission: :class:`bool` | :class:`discord.Permissions`, optional
            Permissions that a user needs to have in order to execute the command, default ``True``.
                If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
        guild_id: :class:`int` | :class:`str`, optional
            The ID of the guild where the permissions should be updated.
                This needs to be passed when you use the `permissions` parameter or want to update a guild command
        permissions: :class:`SlashPermission`, optional
            The new permissions for the command
        global_command: :class:`bool`, optional
            If the command is a global command or a guild command; default ``False``

        Raises
        -------
        :class:`ClientException`
            No command with that name was found 
    
        """
        if guild_id is not None:
            guild_id = int(guild_id)
        typ = CommandType.from_string(typ).value
        if global_command is True:
            api_command = await self._get_global_api_command(name, typ)
        else:
            api_command = await self._get_guild_api_command(name, typ, guild_id)
        if api_command is None:
            raise ClientException("Slash command with name " + str(name) + " and type " + str(typ) + " not found in the api!")
        if permissions is not None:
            await self.http.update_command_permissions(guild_id, api_command["id"], permissions.to_dict())
        if default_permission is not None:
            default_permission = default_permission or False
            api_command["default_permission"] = default_permission
            if global_command is True:
                await self.http.edit_global_command(api_command["id"], api_command)
            else:
                await self.http.edit_guild_command(api_command["id"], guild_id, api_command)
    
    def _add_to_cache(self, base: _C, is_base=False) -> _C:
        if base.has_aliases and is_base is False:
            for a in base.__aliases__:
                cur = base.copy()
                cur.name = a
                self._add_to_cache(cur, is_base=True)
        self.commands.add(base)
        return base

    async def delete_global_commands(self):
        """**Deletes all global commands**"""
        await self.http.delete_global_commands()
    async def delete_guild_commands(self, guild_id: str):
        """
        **Deletes all commands in a guild**

        Parameters
        ----------
        guild_id: :class:`str`
            The id of the guild where all commands are going to be deleted
        
        """
        await self.http.delete_guild_commands(guild_id)
    async def nuke_commands(self):
        """**Deletes every command for the bot, including globals and commands in every guild**"""
        logging.debug("nuking...")
        await self.delete_global_commands()
        logging.debug("nuked global commands")
        async for guild in self._discord.fetch_guilds():
            logging.debug("nuking commands in" + str(guild.id))
            await self.delete_guild_commands(guild.id)
            logging.debug("nuked commands in" + str(guild.name) + " (" + str(guild.id) + ")")
        logging.info("nuked all commands")
    
    def add_build(self, builder):
        """Adds a subclass of `SlashBuilder` to the internal cache and creates the command in the api
        
        Parameters
        ----------
        builder: :class:`~SlashBuilder`
            The built SlashCommand you want to add
        
        """
        builder.register(self)

    def add_command(self, name=None, callback=None, description=None, options=None, guild_ids=None, default_permission=True, guild_permissions=None, api=False) -> Union[SlashCommand, Coroutine]:
        """
        Adds a new slashcommand

        name: :class:`str`
            1-32 characters long name; default MISSING

            .. note::

                The name will be corrected automaticaly (spaces will be replaced with "-" and the name will be lowercased)
        callback: :class:`function`, optional
            A callback that will be called when the command was received
        description: :class:`str`, optional
            1-100 character description of the command; default the command name
        options: List[:class:`~SlashOptions`], optional
            The parameters for the command; default MISSING
        choices: List[:class:`tuple`] | List[:class:`dict`], optional
            Choices for string and int types for the user to pick from; default MISSING
        guild_ids: List[:class:`str` | :class:`int`], optional
            A list of guild ids where the command is available; default MISSING
        default_permission: :class:`bool` | :class:`discord.Permissions`, optional
           Permissions that a user needs to have in order to execute the command, default ``True``.
                    If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
        guild_permissions: Dict[``guild_id``: :class:`~SlashPermission`]
            The permissions for the command in guilds
                Format: ``{"guild_id": SlashPermission}``
        api: :class:`bool`, optional
            Whether the command should be registered to the api (True) or just added in the internal cache
                If it's added to the internal cache, it will be registered to the api when calling the `sync_commands` function.
                If ``api`` is True, this function will return a promise

        Raises
        -------
        :class:`ClientException`
            Commands should be synced but the client is not ready yet
        """
        command = SlashCommand(callback, name, description, options, guild_ids=guild_ids, default_permission=default_permission, 
            guild_permissions=guild_permissions, state=self._discord._connection)
        self._add_to_cache(command)
        if api is True:
            if self.ready is False:
                raise ClientException("Slashcommands are not ready yet")
            return self.create_command(command) 
        return command
    def command(self, name=None, description=None, options=None, guild_ids=None, default_permission=True, guild_permissions=None) -> Callable[..., SlashCommand]:
        """
        A decorator for a slash command
        
        command in discord:
            ``/name [options]``

        Parameters
        ----------
        name: :class:`str`, optional
            1-32 characters long name; default MISSING
            
            .. note::

                The name will be corrected automaticaly (spaces will be replaced with "-" and the name will be lowercased)
        
        description: :class:`str`, optional
            1-100 character description of the command; default the command name
        options: List[:class:`~SlashOptions`], optional
            The parameters for the command; default MISSING
        choices: List[:class:`tuple`] | List[:class:`dict`], optional
            Choices for string and int types for the user to pick from; default MISSING
        guild_ids: List[:class:`str` | :class:`int`], optional
            A list of guild ids where the command is available; default MISSING
        default_permission: :class:`bool` | :class:`discord.Permissions`, optional
            Permissions that a user needs to have in order to execute the command, default ``True``.
                If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
        guild_permissions: Dict[``guild_id``: :class:`~SlashPermission`]
            The permissions for the command in guilds
                Format: ``{"guild_id": SlashPermission}``

        Decorator
        ---------
        callback: :class:`method(ctx)`
            The asynchron function that will be called if the command was used
                ctx: :class:`~SlashInteraction`
                    The used slash command

                .. note::

                    ``ctx`` is just an example name, you can use whatever you want for that

        Example
        -------
        .. code-block::

            @slash.command(name="hello_world", description="This is a test command", 
            options=[
                SlashOption(str, name="parameter", description="this is a parameter", choices=[("choice 1", "test")])
            ], guild_ids=[785567635802816595], default_permission=False, 
            guild_permissions={
                    785567635802816595: SlashPermission(allowed={"539459006847254542": SlashPermission.USER})
                }
            )
            async def command(ctx, parameter = None):
                ...
        """
        def wrapper(callback):
            return self.add_command(name, callback, description, options, guild_ids, default_permission, guild_permissions)
        return wrapper
    def add_subcommand(self, base_names, name=None, callback=None, description=None, options=None, guild_ids=None, default_permission=True, guild_permissions=None):
        return self._add_to_cache(SlashSubcommand(callback, base_names, name, description, options, guild_ids=guild_ids, default_permission=default_permission, guild_permissions=guild_permissions))
    def subcommand(self, base_names, name=None, description=None, options=None, guild_ids=None, default_permission=True, guild_permissions=None):
        """
        A decorator for a subcommand group
        
        command in discord
            ``/base_names... name [options]``

        Parameters
        ----------
        base_names: List[:class:`str`] | :class:`str`
            The names of the parent bases, currently limited to 2
                If you want to make a subcommand (``/base name``), you have to use a str instead of a list
        name: :class:`str`, optional
            1-32 characters long name; default MISSING
            
            .. note::

                The name will be corrected automaticaly (spaces will be replaced with "-" and the name will be lowercased)
        description: :class:`str`, optional
            1-100 character description of the command; default the command name
        options: List[:class:`~SlashOptions`], optional
            The parameters for the command; default MISSING
        choices: List[:class:`tuple`] | List[:class:`dict`], optional
            Choices for string and int types for the user to pick from; default MISSING
        guild_ids: List[:class:`str` | :class:`int`], optional
            A list of guild ids where the command is available; default MISSING
        default_permission: :class:`bool` | :class:`discord.Permissions`, optional
            Permissions that a user needs to have in order to execute the command, default ``True``. 
                If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
        guild_permissions: Dict[``guild_id``: :class:`~SlashPermission`]
            The permissions for the command in guilds
                Format: ``{"guild_id": SlashPermission}``

        .. note::

            Permissions will be the same for every subcommand with the same base

        Decorator
        ---------
        callback: :class:`method(ctx)`
            The asynchron function that will be called if the command was used
                ctx: :class:`~SubSlashInteraction`
                    The used slash command

                .. note::

                    ``ctx`` is just an example name, you can use whatever you want for that
        
        Example
        -------
        
        subcommand

        .. code-block::

            @slash.subcommand_group(base_names="hello", name="world", options=[
                SlashOption(argument_type="user", name="user", description="the user to tell the holy words")
            ], guild_ids=[785567635802816595])
            async def command(ctx, user):
                ...

        subcommand-group

        .. code-block::

            @slash.subcommand_group(base_names=["hello", "beautiful"], name="world", options=[
                SlashOption(argument_type="user", name="user", description="the user to tell the holy words")
            ], guild_ids=[785567635802816595])
            async def command(ctx, user):
                ...

        """
        def wrapper(callback):
            return self._add_to_cache(SlashSubcommand(
                callback, base_names, name, description, options=options, 
                guild_ids=guild_ids, default_permission=default_permission, guild_permissions=guild_permissions,
                state=self._discord._connection
            ))
        return wrapper
    def user_command(self, name=None, guild_ids=None, default_permission=True, guild_permissions=None):
        """
        Decorator for user context commands in discord.
            ``Right-click username`` -> ``apps`` -> ``commands is displayed here``


        Parameters
        ----------
        name: :class:`str`, optional
            The name of the command; default MISSING
        guild_ids: List[:class:`str` | :class:`int`]
            A list of guilds where the command can be used
        default_permission: :class:`bool` | :class:`discord.Permissions`, optional
            Permissions that a user needs to have in order to execute the command, default ``True``.
                    If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
        guild_permissions: Dict[:class:`SlashPermission`], optional
            Special permissions for guilds; default MISSING

        Decorator
        ---------
        callback: :class:`method(ctx, user)`
            The asynchron function that will be called if the command was used
                ctx: :class:`~SubSlashInteraction`
                    The used slash command
                user: :class:`discord.Member`
                    The user on which the command was used
                
                .. note::

                    ``ctx`` and ``user`` are just example names, you can use whatever you want for that

        Example
        -------
        
        .. code-block::

            @slash.user_command(name="call", guild_ids=[785567635802816595], default_permission=False, guild_permissions={
                785567635802816595: SlashPermission(allowed={
                    "585567635802816595": SlashPermission.USER
                })
            })
            async def call(ctx, message):
                ...
        """
        def wrapper(callback) -> UserCommand:
            return self._add_to_cache(UserCommand(callback, name, guild_ids, default_permission, guild_permissions, state=self._discord._connection))
        return wrapper
    def message_command(self, name=None, guild_ids=None, default_permission=True, guild_permissions=None):
        """
        Decorator for message context commands in discord.
            ``Right-click message`` -> ``apps`` -> ``commands is displayed here``


        Parameters
        ----------
        name: :class:`str`, optional
            The name of the command; default MISSING
        guild_ids: List[:class:`str` | :class:`int`]
            A list of guilds where the command can be used
        default_permission: :class:`bool` | :class:`discord.Permissions`, optional
            Permissions that a user needs to have in order to execute the command, default ``True``.
                If a bool was passed, it will indicate whether all users can use the command (``True``) or not (``False``)
        guild_permissions: Dict[:class:`SlashPermission`], optional
            Special permissions for guilds; default MISSING

        Decorator
        ---------
        callback: :class:`method(ctx, message)`
            The asynchron function that will be called if the command was used
                ctx: :class:`~SubSlashInteraction`
                    The used slash command
                message: :class:`~Message`
                    The message on which the command was used
            
                .. note::

                    ``ctx`` and ``message`` are just example names, you can use whatever you want for that
    
        Example
        -------
        
        .. code-block::

            @slash.message_command(name="quote", guild_ids=[785567635802816595], default_permission=False, guild_permissions={
                785567635802816595: SlashPermission(allowed={
                    "585567635802816595": SlashPermission.USER
                })
            })
            async def quote(ctx, message):
                ...
        """
        def wrapper(callback):
            return self._add_to_cache(MessageCommand(callback, name, guild_ids, default_permission, guild_permissions, state=self._discord._connection))
        return wrapper

class Components():
    """
    A class for using and receiving message components in discord
    
    Parameters
    -----------
    client: :class:`discord.Client`
        The main discord client

    override_dpy: :class:`bool`
        Whether some of discord.py's default methods should be overriden with this libary's; Default ``True``
            For more information see https://github.com/discord-py-ui/discord-ui/blob/main/discord_ui/override.py

    auto_defer: Tuple[:class:`bool`, :class:`bool`]
        Settings for the auto-defer; Default ``(True, False)``

        ``[0]``: Whether interactions should be deferred automatically

        ``[1]``: Whether the deferration should be hidden (True) or public (False)

    Example
    ------------------
    Example for using the listener

    
    .. code-block::

        ...
        # Your bot declaration should be here
        components = Components(client)
        
    
    for listening to button presses, use
    
    .. code-block::

        ...
        @client.event("on_button_press")
        async def on_button(pressedButton):
            ...


    for listening to select menu selections, use

    .. code-block::

        ...
        @client.event("on_menu_select")
        async def on_select(seletedMenu):
            ...

    For components that will listen to a custom id, use

    .. code-block::

        ...
        @components.listening_component(custom_id="custom_id_here")
        async def my_func(ctx):
            ...

    """
    def __init__(self, client: commands.Bot, override_dpy=True, auto_defer=False):
        """
        Creates a new compnent listener
        
        Example
        ```py
        Components(client, auto_defer=(True, False))
        ```
        """
        if override_dpy:
            override_it()

        self.auto_defer: Tuple[bool, bool] = (auto_defer, False) if isinstance(auto_defer, bool) else auto_defer
        self.listening_components: Dict[str, List[ListeningComponent]] = {}
        """A list of components that are listening for interaction"""
        self._discord: commands.Bot = client
        self._discord._connection._component_listeners = {}
        if discord.__version__.startswith("2"):
            self._discord.add_listener(self._on_component_response, "on_socket_raw_receive")
        elif discord.__version__.startswith("1"):
            self._discord.add_listener(self._on_component_response, 'on_socket_response')

        old_add = self._discord.add_cog
        def add_cog_override(*args, **kwargs):
            cog = args[0] if len(args) > 0 else kwargs.get("cog")
            for com in self._get_listening_cogs(cog):
                com.cog = cog
                if self.listening_components.get(com.custom_id) is None:
                    self.listening_components[com.custom_id] = []
                self.listening_components[com.custom_id].append(com)
            old_add(*args, **kwargs)
        self._discord.add_cog = add_cog_override

        old_remove = self._discord.remove_cog
        def remove_cog_override(*args, **kwargs):
            cog = args[0] if len(args) > 0 else kwargs.get("cog")
            for com in self._get_listening_cogs(cog):
                com.cog = cog
                self.remove_listening_component(com)
            old_remove(*args, **kwargs)
        self._discord.remove_cog = remove_cog_override
    
    async def _on_component_response(self, msg):
        if discord.__version__.startswith("2"):
            if isinstance(msg, bytes):
                raise NotImplementedError("decompressing was removed! Please upgrade your discord.py version")
            if isinstance(msg, str):
                msg = json.loads(msg)
        
        if msg["t"] != "INTERACTION_CREATE":
            return
        data = msg["d"]
        
        if data["type"] != 3:
            return
        
        user = discord.Member(data=data["member"], guild=self._discord._connection._get_guild(int(data["guild_id"])), state=self._discord._connection) if data.get("member") is not None else discord.User(state=self._discord._connection, data=data["user"])
        if user.dm_channel is None:
            await user.create_dm()
        msg = await getMessage(self._discord._connection, data=data, response=True)
        
        interaction = Interaction(self._discord._connection, data, user, msg)
        if self.auto_defer[0] is True:
            await interaction.defer(self.auto_defer[1])
        self._discord.dispatch("interaction_received", interaction)

        self._discord.dispatch("component", ComponentContext(self._discord._connection, data, user, msg))


        # Handle auto_defer
        if int(data["data"]["component_type"]) == 2:
            for x in msg.buttons:
                if hasattr(x, 'custom_id') and x.custom_id == data["data"]["custom_id"]:
                    component = PressedButton(data, user, x, msg, self._discord)
        elif int(data["data"]["component_type"]) == 3:
            for x in msg.select_menus:
                if x.custom_id == data["data"]["custom_id"]:
                    component = SelectedMenu(data, user, x, msg, self._discord)
        component._handle_auto_defer(self.auto_defer)
        
        
        # dispatch client events before listeners so the exception wont stop executing the function
        if ComponentType(data["data"]["component_type"]) is ComponentType.Button:
            self._discord.dispatch("button_press", component)
        elif ComponentType(data["data"]["component_type"]) is ComponentType.Select:
            self._discord.dispatch("menu_select", component)
        
        # Get listening components with the same custom id
        listening_components = self.listening_components.get(data["data"]["custom_id"])
        if listening_components is not None:
            for listening_component in listening_components:
                await listening_component.invoke(component)

        
        listener: Listener = self._discord._connection._component_listeners.get(str(msg.id))
        if listener is not None:
            await listener._call_listeners(component)


    async def send(self, channel, content=MISSING, *, tts=False, embed=MISSING, embeds=MISSING, file=MISSING, 
            files=MISSING, delete_after=MISSING, nonce=MISSING, allowed_mentions=MISSING, reference=MISSING, 
            mention_author=MISSING, components=MISSING) -> Message:
        """
        Sends a message to a textchannel

        Parameters
        ----------
        channel: :class:`discord.TextChannel` | :class:`int` | :class:`str`
            The target textchannel or the id of it
        content: :class:`str`, optional
            The message text content; default None
        tts: :class:`bool`, optional
            True if this is a text-to-speech message; default False
        embed: :class:`discord.Message`, optional
            Embedded rich content (up to 6000 characters)
        embeds: List[:class:`discord.Embed`], optional
            Up to 10 embeds; default None
        file: :class:`discord.File`, optional
            A file sent as an attachment to the message; default None
        files: List[:class:`discord.File`], optional
            A list of file attachments; default None
        delete_after: :class:`float`, optional
            After how many seconds the message should be deleted; default None
        nonce: :class:`int`, optional
            The nonce to use for sending this message. If the message was successfully sent, then the message will have a nonce with this value; default None
        allowed_mentions: :class:`discord.AllowedMentions`, optional
            A list of mentions proceeded in the message; default None
        reference: :class:`discord.MessageReference` | :class:`discord.Message`, optional
            A message to refer to (reply); default None
        mention_author: :class:`bool`, optional
            True if the author should be mentioned; default None
        components: List[:class:`~Button` | :class:`~LinkButton` | :class:`~SelectMenu`], optional
            A list of message components included in this message; default None

        Raises
        ------
        :class:`WrongType`
            Channel is not an instance of :class:`discord.abc.GuildChannel`, :class:`discord.abc.PrivateChannel:, :class:`int`, :class:`str` 


        Returns
        -------
        :class:`~Message`
            Returns the sent message
        """

        if not isinstance(channel, (discord.abc.GuildChannel, int, str, discord.User, discord.abc.PrivateChannel)):
            raise WrongType("channel", channel, ["discord.abc.PrivateChannel", "discord.abc.GuildChannel", "discord.User", "int"])

        channel_id = None
        if isinstance(channel, discord.User):
            if channel.dm_channel is None:
                channel = await channel.create_dm()
                channel_id = channel.id
            else:
                channel_id = channel.dm_channel
        elif isinstance(channel, discord.TextChannel):
            channel_id = channel.id
        else: 
            channel_id = channel
        payload = get_message_payload(content=content, tts=tts, embed=embed, embeds=embeds, nonce=nonce, allowed_mentions=allowed_mentions, reference=reference, mention_author=mention_author, components=components)

        route = BetterRoute("POST", f"/channels/{channel_id}/messages")

        r = None
        if file is MISSING and files is MISSING:
            r = await self._discord.http.request(route, json=payload)
        else:
            r = await send_files(route, files=_or(files, [file]), payload=payload, http=self._discord.http)

        msg = Message(state=self._discord._connection, channel=channel, data=r)
        
        if not _none(delete_after):
            await msg.delete(delay=delete_after)
        
        return msg
    def send_webhook(self, webhook, content=MISSING, *, wait=False, username=MISSING, avatar_url=MISSING, tts=False, files=MISSING, embed=MISSING, embeds=MISSING, allowed_mentions=MISSING, components=MISSING) -> Union[discord.WebhookMessage, None]:
        """
        Sends a webhook message
        
        Parameters
        ----------
        webhook: :class:`discord.Webhook`
            The webhook which will send the message
        content: :class:`str`, optional
            the message contents (up to 2000 characters); default None
        wait: :class:`bool`, optional
            if `True`, waits for server confirmation of message send before response, and returns the created message body; default False
        username: :class:`str`, optional
            override the default username of the webhook; default None
        avatar_url: :class:`str`, optional
            override the default avatar of the webhook; default None
        tts: :class:`bool`, optional
            true if this is a TTS message; default False
        files: :class:`discord.File`
            A list of files which will be sent as attachment
        embed: :class:`discord.Embed`
            Embed rich content, optional
        embeds: List[:class:`discord.Embed`], optional
            embedded rich content; default None
        allowed_mentions: :class:`discord.AllowedMentions`, optional
            allowed mentions for the message; default None
        components: List[:class:`~Button` | :class:`~LinkButton` | :class:`~SelectMenu`], optional
            the message components to include with the message; default None
        
        Returns
        -------
        :class:`~WebhookMessage` | :class:`None`
            The message which was sent, if wait was True, else nothing will be returned
        
        """
        payload = get_message_payload(content, tts=tts, embed=embed, embeds=embeds, allowed_mentions=allowed_mentions, components=components)
        payload["wait"] = wait
        if username is not None:
            payload["username"] = username
        if avatar_url is not None:
            payload["avatar_url"] = str(avatar_url)

        return webhook._adapter.execute_webhook(payload=payload, wait=wait, files=files)
    def listening_component(self, custom_id, messages=None, users=None, 
        component_type: Literal["button", "select"]=None,
        check: Callable[[Union[PressedButton, SelectedMenu]], bool]=EMPTY_CHECK
    ):
        """
        Decorator for ``add_listening_component``

        Parameters
        ----------
        custom_id: :class:`str`
            The custom_id of the components to listen to
        messages: List[:class:`discord.Message` | :class:`int` :class:`str`], Optional
            A list of messages or message ids to filter the listening component
        users: List[:class:`discord.User` | :class:`discord.Member` | :class:`int` | :class:`str`], Optional
            A list of users or user ids to filter
        component_type: Literal[``'button'`` | ``'select'``]
            What type the used component has to be of (select: SelectMenu, button: Button)
        check: :class:`function`, Optional
            A function that has to return True in order to invoke the listening component
                The check function takes to parameters, the component and the message

        Decorator
        ---------
            callback: :class:`method(ctx)`
                The asynchron function that will be called if a component with the custom_id was invoked

                There will be one parameters passed

                    ctx: :class:`~PressedButton` or :class:`~SelectedMenu`
                        The invoked component
                    
                    .. note::

                        ``ctx`` is just an example name, you can use whatever you want for it

        Example
        -------
        .. code-block::

            @ui.components.listening_component("custom_id", [539459006847254542], [53945900682362362])
            async def callback(ctx):
                ...
            
        """
        def wrapper(callback: Callable[[Union[PressedButton, SelectedMenu]], Coroutine[Any, Any, Any]]):
            self.add_listening_component(callback, custom_id, messages, users, component_type, check)
        return wrapper
    def add_listening_component(self, callback, custom_id, messages=None, users=None, component_type: Literal["button", 2, "select", 3]=None, check: Callable[[Union[Component, Button, SelectMenu]], bool]=EMPTY_CHECK):
        """
        Adds a listener to received components

        Parameters
        ----------
        callback: :class:`function`
            The callback function that will be called when the component was received
        custom_id: :class:`str`
            The custom_id of the components to listen to
        messages: List[:class:`discord.Message` | :class:`int` :class:`str`], Optional
            A list of messages or message ids to filter the listening component
        users: List[:class:`discord.User` | :class:`discord.Member` | :class:`int` | :class:`str`], Optional
            A list of users or user ids to filter
        component_type: :class:`str` | :class:`int`
            The type of which the component has to be
        check: :class:`function`, Optional
            A function that has to return True in order to invoke the listening component
                The check function takes to parameters, the component and the message

        Raises
        -------
        :class:`MissingListenedComponentParameters`
            The callback for the listening component is missing required parameters
        :class:`NoAsyncCallback`
            The callback is not defined with the `async` keyword
        """
        if not inspect.iscoroutinefunction(callback):
            raise NoAsyncCallback()
        if len(inspect.signature(callback).parameters) < 1:
            raise MissingListenedComponentParameters()
        
        if self.listening_components.get(custom_id) is None:
            self.listening_components[custom_id] = []
        self.listening_components[custom_id].append(ListeningComponent(callback, messages, users, component_type, check, custom_id))
    def remove_listening_components(self, custom_id):
        """
        Removes all listening components for a custom_id
        
        Parameters
        ----------
        custom_id: :class:`str`
            The custom_id for the listening component
        
        """
        if self.listening_components.get(custom_id) is not None:
            del self.listening_components[custom_id]
    def remove_listening_component(self, listening_component):
        """
        Removes a listening component
        
        Parameters
        ----------
        listening_component: :class:`ListeningComponent`
            The listening component which should be removed
        
        """
        with contextlib.supress(KeyError): 
            self.listening_components[listening_component.custom_id].remove(listening_component)

    def _get_listening_cogs(self, cog):
        return [x[1] for x in inspect.getmembers(cog, lambda x: isinstance(x, ListeningComponent))]

    async def put_listener_to(self, target_message, listener):
        """Adds a listener to a message and edits it if the components are missing
        
        Parameters
        ----------
        target_message: :class:`Message`
            The message to which the listener should be attached
        listener: :class:`Listener`
            The listener which should be put to the message
        
        """
        if len(target_message.components) == 0:
            await target_message.edit(components=listener.to_components())
        self.attach_listener_to(target_message, listener)

    def attach_listener_to(self, target_message, listener):
        """Attaches a listener to a message after it was sent
        
        Parameters
        ----------
        target_message: :class:`Message`
            The message to which the listener should be attached
        listener: :class:`Listener`
            The listener that will be attached
        
        """
        listener._start(target_message, target_message)
    def clear_listeners(self):
        """Removes all component listeners"""
        self._connection._component_listeners = {}

class UI():
    """
    The main extension for the package to use slash commands and message components
        
        Parameters
        ----------
        client: :class:`discord.ext.commands.Bot`
            The discord bot client

        override_dpy: :class:`bool`
            Whether some of discord.py's default methods should be overriden with this libary's; Default ``True``
                For more information see https://github.com/discord-py-ui/discord-ui/blob/main/discord_ui/override.py

        slash_options: :class:`dict`, optional
            Settings for the slash command part; Default `{parse_method: ParseMethod.AUTO, delete_unused: False, wait_sync: 1}`
            
            ``parse_method``: :class:`int`, optional
                How the received interaction argument data should be treated; Default ``ParseMethod.AUTO``

            ``auto_sync``: :class:`bool`, optional
                Whether the libary should sync the slash commands automatically; Default ``True``

            ``delete_unused``: :class:`bool`, optional
                Whether the commands that are not registered by this slash ui should be deleted in the api; Default ``False``

            ``sync_on_cog``: :class:`bool`, optional
                Whether the slashcommands should be updated whenever a new cog is added or removed; Default ``True``

            ``wait_sync``: :class:`float`, optional
                How many seconds will be waited until the commands are going to be synchronized; Default ``1``

    auto_defer: Tuple[:class:`bool`, :class:`bool`]
        Settings for the auto-defer; Default ``(True, False)``

        ``[0]``: Whether interactions should be deferred automatically

        ``[1]``: Whether the deferration should be hidden (True) or public (False)
    """
    def __init__(self, client, override_dpy=True, slash_options = {"parse_method": ParseMethod.AUTO, "auto_sync": True, "delete_unused": False, "sync_on_cog": True, "wait_sync": 1}, auto_defer = False) -> None:
        """
        Creates a new ui object
        
        Example
        ```py
        UI(client, slash_options={"delete_unused": True, "wait_sync": 2}, auto_defer=True)
        ```
        """
        # enable debug events if needed
        if discord.__version__.startswith("2"):
            client._enable_debug_events = True

        self.components: Components = Components(client, override_dpy=override_dpy, auto_defer=auto_defer)
        """For using message components"""
        self.logger = logging
        if slash_options is None:
            slash_options = {"resolve_data": True, "delete_unused": False, "wait_sync": 1, "auto_defer": auto_defer}
        if slash_options.get("auto_defer") is None:
            slash_options["auto_defer"] = auto_defer
        self.slash: Slash = Slash(client, **slash_options)
        """For using slash commands"""
        
        # region shortcuts
        self.listening_component = self.components.listening_component
        self.command = self.slash.command
        self.subcommand = self.slash.subcommand
        self.message_command = self.slash.message_command
        self.user_command = self.slash.user_command
        # endregion
