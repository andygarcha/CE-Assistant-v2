from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Game import CEGame
from Classes.OtherClasses import UpdateMessage
import Modules.hm as hm

def user_update(user : CEUser, site_data : CEUser, database_name : list[CEGame]) -> tuple[list[UpdateMessage], CEUser] :
    """Takes in a user and updates it, and returns a list of things to send."""
    updates : list[UpdateMessage] = []

    original_points = user.get_total_points()
    original_completed_games = user.get_completed_games_2(database_name)
    original_rank = user.get_rank()

    user.owned_games = site_data.owned_games

    new_points = user.get_total_points()
    new_completed_games = user.get_completed_games_2(database_name)
    new_rank = user.get_rank()

    # search for newly completed games
    for game in new_completed_games :

        # if game is too low anyway, skip it
        TIER_MINIMUM = 4
        if not game.get_tier_num() >= TIER_MINIMUM : continue

        # check to see if it was completed before
        for old_game in original_completed_games :
            # it was completed before
            if game.ce_id == old_game.ce_id : continue
        
        updates.append(UpdateMessage(
            location="log",
            message=(f"Wow <@{user.discord_id}>! You've completed {game.game_name}, a {game.get_tier_emoji()} " + 
                     f"worth {game.get_total_points()} points {hm.get_emoji('Points')}!")
        ))

    # rank update
    if new_rank != original_rank and new_points > original_points :
        updates.append(UpdateMessage(
            location="log",
            message=(f"Congrats to <@{user.discord_id}> for ranking up from Rank {hm.get_emoji(original_rank)} " +
                     f"to Rank {hm.get_emoji(new_rank)}!")
        ))

    # check rolls
    for roll in user.current_rolls :
        if roll.is_won() :
            ""