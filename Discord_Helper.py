"""
This module is made to help me with my discord stuff.
It will:

- take in a `CERoll` object and return an array of `discord.Embed`s denoting exactly what's up.
"""
import datetime
import json

import requests
from CE_Roll import CERoll
import discord
import Mongo_Reader
import CEAPIReader
import hm

def get_roll_embeds(roll : CERoll, database_user : list, database_name : list) -> list[discord.Embed] :
    from CE_Game import CEGame

    # -- set up the array --
    embeds : list[discord.Embed] = []

    # -- set up the intro embed --
    embeds[0] = discord.Embed(
        title=roll.get_roll_name(),
        timestamp=datetime.datetime.now(),
        color = 0x000000
    )
    embeds[0].set_footer(
        text = f'Page 1 of {str(len(roll.get_games()) + 1)}',
        icon_url = hm.final_ce_icon
    )
    embeds[0].set_author(name="Challenge Enthusiasts")

    # -- set up description --
    description = "__Rolled Games__\n"
    for i, id in roll.get_games() :
        game : CEGame = hm.get_item_from_list(id, database_name)
        description += f"{i + 1}. {game.get_game_name()}\n"
    
    # -- set up roll info --
    description += "__Roll Info__\n"
    if roll.ends() :
        description += f"You must complete {roll.get_roll_name()} by <t:{roll.get_due_time()}>.\n"
        description += f"If you fail, you will have a cooldown until {roll.calculate_cooldown_date()}.\n"
    else :
        description += f"{roll.get_roll_name()} has no time limit. You can reroll on {roll.calculate_cooldown_date()}.\n"

    # -- set the description --
    embeds[0].description = description

    # -- now grab all the other embeds --
    for i, id in enumerate(roll.get_games()) :
        embeds.append(get_game_embed(id))
        embeds[i+1].set_footer(
            text=f"Page {i+2} of {len(roll.get_games()) + 1}",
            icon_url = hm.final_ce_icon
        )

    return embeds





def get_game_embed(game_id : str) -> discord.Embed :
    from CE_Game import CEGame

    # -- get the api data --
    game : CEGame = CEAPIReader.get_api_page_data('game', game_id)
    if game == None : return None

    # -- instantiate the embed --
    embed = discord.Embed(
        title = f"[{game.get_game_name()}](https://cedb.me/game/{game_id})",
        description = "To be determined.",
        color = 0x000000,
        timestamp = datetime.datetime.now()
    )
    embed.set_author(name='Challenge Enthusiasts', icon_url=hm.ce_mountain_icon)

    # -- get steam data and set image and description --
    steam_data = game.get_steam_data()
    embed.set_image(steam_data[game.get_platform_id()]['data']['header_image'])
    embed.description = (
        f"- {hm.get_emoji(game.get_tier())}{hm.get_emoji(game.get_category())}" +
        f" - {game.get_total_points()}{hm.get_emoji('Points')}\n"
    )

    # -- set up price --
    if steam_data[game.get_platform_id()]['data']['is_free'] :
        embed.description += "- Price: Free\n"
    elif 'price_overview' in steam_data[game.get_platform_id()]['data'] :
        embed.description += (f"- Price: {steam_data[game.get_platform_id()]['data']['price_overview']['final_formatted']}\n")
    else :
        embed.description += "- Price unavailable.\n"

    # -- add steamhunters data --
    embed.description += f"- SteamHunters Median Completion Time: {game.get_steamhunters_data()}\n"
    
    # -- get ce data --
    completion_data = game.get_completion_data()
    embed.description += f"- Total Owners: {completion_data['total']}\n"
    embed.description += f"- Full Completions: {completion_data['completed']}"
    if completion_data['total'] != 0 :
        embed.description += f"({(completion_data['completed'] / completion_data['total']) * 100}%)\n"
    else :
        embed.description += "N/A%\n"

    return embed




async def get_buttons(view : discord.ui.View, embeds : list[discord.Embed]):
    if len(embeds) == 1 : return
    currentPage = 1
    page_limit = len(embeds)
    buttons = [discord.ui.Button(label=">", style=discord.ButtonStyle.green, disabled=False), discord.ui.Button(label="<", style=discord.ButtonStyle.red, disabled=True)]
    view.add_item(buttons[1])
    view.add_item(buttons[0])

    for i, embed in enumerate(embeds):
        embed.set_footer(text=f"Page {i+1} of {page_limit}")

    async def hehe(interaction : discord.Interaction):
        return await callback(interaction, num=1)

    async def haha(interaction : discord.Interaction):
        return await callback(interaction, num=-1)

    async def callback(interaction : discord.Interaction, num : int):
        nonlocal currentPage, view, embeds, page_limit, buttons
        currentPage+=num
        if(currentPage >= page_limit) :
            buttons[0].disabled = True
        else : buttons[0].disabled = False
        if(currentPage <= 1) :
            buttons[1].disabled = True
        else : buttons[1].disabled = False
        await interaction.response.edit_message(embed=embeds[currentPage-1], view=view)

    buttons[0].callback = hehe
    buttons[1].callback = haha

    async def disable() :
        for button in buttons :
            button.disabled = True
        print("disabled")

    #view.on_timeout = await disable()