"""
File for managing different discord package imports
"""
__discord_import__ = "n"

from enum import Enum

class ImportVersion(Enum):
    discordpy = "d"
    nextcord = "n"
    pycord = "p"

__import_version__ = ImportVersion(__discord_import__)

import discord
if __import_version__ is ImportVersion.discordpy:
    import discord
    from discord.ext import commands
elif __import_version__ is ImportVersion.nextcord:
    import nextcord as discord
    from nextcord.ext import commands
# elif __import_version__ is ImportVersion.pycord:
#     import pycord as discord
else:
    import discord