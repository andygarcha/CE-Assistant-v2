"""
This module is made to help me with my discord stuff.
It will:

- take in a `CERoll` object and return an array of `discord.Embed`s denoting exactly what's up.
"""
import datetime
import discord
import logging

# -- local --
from Classes.CE_Roll import CERoll
import Modules.hm as hm


# selenium and beautiful soup stuff

logger = logging.getLogger(__name__)

async def get_roll_embeds(roll : CERoll, database_name : list) -> list[discord.Embed] :
    """This function returns an array of `discord.Embed`'s to be sent when a roll is initialized."""
    from Classes.CE_Game import CEGame

    # -- set up the array --
    embeds : list[discord.Embed] = []

    # -- set up the intro embed --
    embeds.append(
        discord.Embed(
            title=roll.roll_name,
            timestamp=datetime.datetime.now(),
            color = 0x000000
        )
    )
    embeds[0].set_footer(
        text = f'Page 1 of {str(len(roll.games) + 1)}',
        icon_url = hm.FINAL_CE_ICON
    )
    embeds[0].set_author(name="Challenge Enthusiasts")

    # -- set up description --
    description = "__Rolled Games__\n"
    for i, id in enumerate(roll.games) :
        game : CEGame = hm.get_item_from_list(id, database_name)
        description += f"{i + 1}. {game.game_name}\n"
    
    # -- set up roll info --
    description += "__Roll Info__\n"
    if roll.ends() :
        description += f"You must complete {roll.roll_name} by <t:{roll.due_time}>.\n"
        description += f"If you fail, you will have a cooldown until <t:{roll.calculate_cooldown_date(database_name=database_name)}>.\n"
    else :
        description += f"{roll.roll_name} has no time limit. You can reroll on <t:{roll.calculate_cooldown_date(database_name=database_name)}>.\n"

    # -- set the description --
    embeds[0].description = description

    # -- now grab all the other embeds --
    for i, id in enumerate(roll.games) :
        embeds.append(await get_game_embed(game_id=id, database_name=database_name))
        embeds[i+1].set_footer(
            text=f"Page {i+2} of {len(roll.games) + 1}",
            icon_url = hm.FINAL_CE_ICON
        )

    return embeds





async def get_game_embed(game_id : str, database_name : list) -> discord.Embed :
    """This function returns a `discord.Embed` that holds all information about a game."""

    # imports and type hinting
    from Classes.CE_Game import CEGame
    database_name : list[CEGame] = database_name

    # grab the game
    game : CEGame = hm.get_item_from_list(game_id, database_name)
    if game is None:
        return None

    # -- instantiate the embed --
    embed = discord.Embed(
        title = game.game_name,
        url=f"https://cedb.me/game/{game_id}",
        description = "To be determined.",
        color = 0x000000,
        timestamp = datetime.datetime.now()
    )
    embed.set_author(name='Challenge Enthusiasts', icon_url=hm.CE_MOUNTAIN_ICON)

    # -- set the image to the ce header --
    embed.set_image(url= (await game.get_ce_api_game()).header)

    # -- get steam data and set and description --

    # TODO: replace these calls with database tier calls
    if game.platform == "steam" :
        price = await game.get_price_async()
    embed.description = (
        f"- {hm.get_emoji(game.get_tier())}{hm.get_emoji(game.category)}" +
        f" - {game.get_total_points()}{hm.get_emoji('Points')}\n"
    )

    # -- set up price --
    if game.platform == "retroachievements" or price is None or price == 0.0 :
        embed.description += "- Price: Free!\n"
    else :
        embed.description += (f"- Price: ${price}\n")

    # -- add steamhunters data --
    sh_data = await game.get_steamhunters_data_async()
    if sh_data is None:
        sh_data = "N/A"
    embed.description += f"- SteamHunters Median Completion Time: {sh_data} hours\n"
    
    # -- get ce data --
    completion_data = await game.get_completion_data()
    embed.description += f"- {completion_data.description()}\n"

    return embed




async def get_buttons(view : discord.ui.View, embeds : list[discord.Embed]):
    if len(embeds) == 1:
        return
    currentPage = 1
    page_limit = len(embeds)
    buttons = [
        discord.ui.Button(
            label=">",
            style=discord.ButtonStyle.green,
            disabled=False
        ), 
        discord.ui.Button(
            label="<",
            style=discord.ButtonStyle.red,
            disabled=True
        )
    ]
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
        else:
            buttons[0].disabled = False

        if(currentPage <= 1) :
            buttons[1].disabled = True
        else:
            buttons[1].disabled = False
        await interaction.response.edit_message(embed=embeds[currentPage-1], view=view)

    buttons[0].callback = hehe
    buttons[1].callback = haha

    async def disable() :
        for button in buttons :
            button.disabled = True
        logger.debug("disabled")

    #view.on_timeout = disable




# set up the view
class ProfileView(discord.ui.View) :
    def __init__(self, summary_embed : discord.Embed, recent_embed : discord.Embed) :
        super().__init__(timeout=None)
        self.__summary_embed = summary_embed
        self.__recent_embed = recent_embed
    
    @discord.ui.button(label="Summary", style=discord.ButtonStyle.gray, disabled=True)
    async def summary_button(self, interaction : discord.Interaction, button : discord.ui.Button) :
        # defer the message
        await interaction.response.defer()

        # un-disable everything
        for child in self.children :
            child.disabled = False
        
        # and disable this one
        button.disabled = True

        # and now edit the message and return
        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=self.__summary_embed,
            view=self
        )

    @discord.ui.button(label="Recent", style=discord.ButtonStyle.gray)
    async def recent_buttton(self, interaction : discord.Interaction, button : discord.ui.Button) :
        # defer the message
        await interaction.response.defer()

        # un-disable everything
        for child in self.children :
            child.disabled = False

        # but disable this one
        button.disabled = True

        # and now edit the mesasge
        return await interaction.followup.edit_message(
            message_id=interaction.message.id,
            embed=self.__recent_embed,
            view=self
        )


async def get_user_embeds(user, database_name : list) -> tuple[discord.Embed, discord.ui.View] :
    """Returns a `discord.Embed` that represents this user.""" 

    # imports and type hintin
    from Classes.CE_User import CEUser
    from Classes.CE_Game import CEGame
    user : CEUser = user
    database_name : list[CEGame] = database_name

    # pull api data
    api_user = await user.get_api_user()
    if api_user is None:
        return (discord.Embed(title="Error!"), discord.ui.View())

    # -- two embeds: summary, completions --
    # summary
    summary_embed = discord.Embed(
        title="Profile",
        color=0xff9494,
        timestamp=datetime.datetime.now()
    )
    summary_embed.add_field(
        name="User",
        value = f"<@{user.discord_id}> {hm.get_emoji(user.get_rank())}",
        inline=True
    )
    summary_embed.add_field(
        name = "Current Values",
        value = f"{user.get_total_points()} {hm.get_emoji('Points')} - Casino Score: {user.casino_score}",
        inline=True
    )
    summary_embed.add_field(
        name = "CR",
        value=user.get_cr(database_name=database_name).cr_string(),
        inline=False
    )
    summary_embed.add_field(
        name="Completions",
        value=api_user.tier_genre_summary_str(),
        inline=False
    )

    # recent
    recent_embed = discord.Embed(
        title="Profile",
        color=0xff9494,
        timestamp=datetime.datetime.now()
    )
    recent_embed.add_field(
        name="Recent Completions",
        value=api_user.most_recent_objectives_str()
    )
    recent_embed.add_field(
        name="Monthly Breakdown",
        value=api_user.monthly_report_str()
    )


    return (summary_embed, ProfileView(summary_embed, recent_embed))

