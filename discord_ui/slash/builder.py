import inspect
from re import A, S


from discord_ui.client import Slash
from ..enums import CommandType, OptionType
from .http import SlashHTTP
from ..tools import try_get
from .types import SlashCommand, SlashOption, SlashOptionCollection, SlashPermission, SlashSubcommand, format_name

from typing import Callable, List, Dict



class Subcommand(SlashSubcommand):
    __slots__ = SlashSubcommand.__slots__ + ("__group__", "build",)
    def __init__(self, callback, name=None, description=None, options=None) -> None:
        super().__init__(callback, base_names=[], name=name, description=description, options=options)
        self.__group__ = getattr(callback, "__group__", None)
        self.build: SlashBuilder = None
    @property
    def group_name(self) -> str:
        return try_get(self.__group__, 0, None)
    @property
    def group_description(self) -> str:
        return try_get(self.__group__, 1, "\u200b")
    @property
    def has_group(self) -> bool:
        return self.__group__ != None
    def to_super_dict(self):
        base = super().to_dict()
        if self.has_group:
            return SlashOption(OptionType.SUB_COMMAND_GROUP, self.group_name, self.group_description, options=[base]).to_dict()
        return base
    async def invoke(self, ctx, *args, **kwargs):
        if self.build != None:
            return await self.callback(self.build, ctx, *args, **kwargs)
        return await self.callback(ctx, *args, **kwargs)
    async def _update_id(self, _http=None):
        id = await super()._update_id(_http=_http)
        if self.build != None:
            self.build._id = id
        return id

class SlashBuilder():
    def __init__(self, name=None, description=None, guild_ids=None, guild_permissions=None, default_permission=True) -> None:
        self.__sync__ = True
        self.__guild_changes__ = {}
        self.__aliases__ = []
        self.__auto_defer__ = None
        self.__choice_generators__ = {}
        self.command_type = CommandType.Slash
        
        self._id = None # set later
        self._name = None
        self._http: SlashHTTP = None # set later
        self.name = name

        self.description: str = description
        self.guild_ids: List[int] = guild_ids
        self.guild_permissions: Dict[int, SlashPermission] = guild_permissions
        self.default_permission = default_permission
        self.permissions = SlashPermission()
        # region no_sub
        # self.callback: Callable = None
        self._options = SlashOptionCollection()
        # endregion
    def __init_subclass__(cls) -> None:
        cls.command_type = CommandType.Slash
    
    async def invoke(self, *args, **kwargs):
        await self.callback(*args, **kwargs)

    @property
    def options(self) -> SlashOptionCollection:
        return self._options
    @options.setter
    def options(self, value):
        self._options = SlashOptionCollection(value)
    async def _fetch_id(self):
        return await SlashCommand._fetch_id(self)
    async def _update_id(self, _http=None):
        return await SlashCommand._update_id(self, _http)

    @property
    def id(self):
        return self._id
    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, value):
        self._name = format_name(value)

    def get_subcommands(self) -> List[Subcommand]:
        return [x[1] for x in inspect.getmembers(self, predicate=lambda x: isinstance(x, Subcommand))]
    def has_groups(self):
        return all(x.has_group for x in self.get_subcommands())
    def has_subs(self):
        return len(self.get_subcommands()) > 0
    def _subs_to_dict(self):
        _commands: List[Subcommand] = [
            (x.group_name, x) for x in
                [x[1] for x in inspect.getmembers(self, predicate=lambda x: isinstance(x, Subcommand))]
        ]
        if not all(x[1].has_group for x in _commands):
            return [x[1].to_super_dict() for x in _commands]
        commands = {}
        for x in _commands:
            if x[0] in commands:
                commands[x[0]]["options"] += x[1].to_supper_dict()["options"]
                continue
            commands[x[0]] = x[1].to_super_dict()
        return list(commands.values())

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "default_permission": self.default_permission,
            "options": self.options.to_dict() if not self.has_subs() else self._subs_to_dict()
        }

    def register(self, slash: Slash):
        if self.has_subs():
            if self.has_groups():
                for x in self.get_subcommands():
                    setattr(getattr(self, f"{x.callback.__name__}"), "build", self)
                    x.base_names = [self.name] + [x.group_name or ()]
                    if slash.subcommands.get(self.name) == None:
                        slash.subcommands[self.name] = {}
                    if slash.subcommands[self.name].get(x.group_name) == None:
                        slash.subcommands[self.name][x.group_name] = {}
                    slash.subcommands[self.name][x.group_name][x.name] = x
            else:
                for x in self.get_subcommands():
                    setattr(getattr(self, f"{x.callback.__name__}"), "build", self)
                    x.base_names = [self.name]
                    if slash.subcommands.get(self.name) == None:
                        slash.subcommands[self.name] = {}
                    slash.subcommands[self.name][x.name] = x
        else:
            slash.commands[self.name] = self
    @property
    def guild_only(self):
        return SlashCommand.guild_only.getter(self)
    @staticmethod
    def subcommand(name, description=None, options=None):
        def wrapper(callback) -> Subcommand:
            return Subcommand(callback, name, description, options)
        return wrapper
    @staticmethod
    def group(name, description=None):
        def wrapper(callback):
            callback.__group__ = (format_name(name), description,)
            return callback
        return wrapper