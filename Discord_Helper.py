"""
This module is made to help me with my discord stuff.
It will:

- take in a `CERoll` object and return an array of `discord.Embed`s denoting exactly what's up.
"""
from CE_Roll import CERoll
import discord

def get_roll_embeds(roll : CERoll) -> list[discord.Embed] :
    ""