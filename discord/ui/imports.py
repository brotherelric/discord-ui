"""This module is for managing different discord packages.

It will autoimport nextcord if installed, otherwise it will import `discord`.
If you want to manually set a version, uncomment the `__import_version__ = ImportVersion.` line.
"""
import discord
from discord.ext import commands