"""This module is for managing different discord packages.

It will autoimport nextcord if installed, otherwise it will import `discord`.
If you want to manually set a version, uncomment the `__import_version__ = ImportVersion.` line.
"""
__discord_import__ = "d"

# Try to import nextcord
try:
    import nextcord
    # if succesfully imported, autosetting version to nextcord
    __discord_import__ = "n"
except ImportError:
    # otherwise set it to discord.py
    __discord_import__ = "d"
from enum import Enum

class ImportVersion(Enum):
    discordpy = "d"
    nextcord = "n"

__import_version__ = ImportVersion(__discord_import__)
# uncomment line to manually set import
# __import_version__ = ImportVersion.


if __import_version__ is ImportVersion.discordpy:
    import discord
    from discord.ext import commands
elif __import_version__ is ImportVersion.nextcord:
    import nextcord as discord
    from nextcord.ext import commands
else:
    import discord