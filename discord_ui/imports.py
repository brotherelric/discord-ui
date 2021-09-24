"""
File for managing different discord package imports
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

if __import_version__ is ImportVersion.discordpy:
    import discord
    from discord.ext import commands
elif __import_version__ is ImportVersion.nextcord:
    import nextcord as discord
    from nextcord.ext import commands
else:
    import discord