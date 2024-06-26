from Classes.CE_User import CEUser
from Classes.CE_User_Game import CEUserGame
from Classes.CE_User_Objective import CEUserObjective
from Classes.CE_Game import CEGame
from Classes.OtherClasses import UpdateMessage
import Modules.hm as hm

def check_category_roles(old_games : list[CEUserGame], new_games : list[CEUserGame],
                         database_name : list[CEGame], user : CEUser
                         ) -> list[UpdateMessage] :
    "Takes in the old and newly completed games and returns a list of `UpdateMessage`s to send."

    # ----- set up variables -----
    oldt1s, oldt2s, oldt3s, oldt4s, oldt5s = (0,)*5
    oldac, oldar, oldbh, oldfp, oldpl, oldst = (0,)*6
    newt1s, newt2s, newt3s, newt4s, newt5s = (0,)*5
    newac, newar, newbh, newfp, newpl, newst = (0,)*6
    updates : list[UpdateMessage] = []

    # ----- sort old games -----
    for game in old_games :
        points = game.get_user_points() # grab the points
        database_game = hm.get_item_from_list(game.ce_id, database_name) # get the official game

        if game.is_completed(database_name) :
            match(database_game.get_tier()) :
                case "Tier 1" : oldt1s += points
                case "Tier 2" : oldt2s += points
                case "Tier 3" : oldt3s += points
                case "Tier 4" : oldt4s += points
                case "Tier 5" : oldt5s += points
                case "Tier 6" : oldt5s += points # t6
                case "Tier 7" : oldt5s += points # t7

        match(database_game.category) :
            case "Action" : oldac += points
            case "Arcade" : oldar += points
            case "Bullet Hell" : oldbh += points
            case "First-Person" : oldfp += points
            case "Platformer" : oldpl += points
            case "Strategy" : oldst += points

    # ----- sort new games -----
    for game in new_games :
        points = game.get_user_points()
        database_game = hm.get_item_from_list(game.ce_id, database_name)
        if game.is_completed(database_name) :
            match(database_game.get_tier()) :
                case "Tier 1" : newt1s += points
                case "Tier 2" : newt2s += points
                case "Tier 3" : newt3s += points
                case "Tier 4" : newt4s += points
                case "Tier 5" : newt5s += points
                case "Tier 6" : newt5s += points # t6
                case "Tier 7" : newt5s += points # t7
        match(database_game.category) :
            case "Action" : newac += points
            case "Arcade" : newar += points
            case "Bullet Hell" : newbh += points
            case "First-Person" : newfp += points
            case "Platformer" : newpl += points
            case "Strategy" : newst += points

    old_categories = (oldac, oldar, oldbh, oldfp, oldpl, oldst)
    new_categories = (newac, newar, newbh, newfp, newpl, newst)
    old_tiers = (oldt1s, oldt2s, oldt3s, oldt4s, oldt5s)
    new_tiers = (newt1s, newt2s, newt3s, newt4s, newt5s)

    CATEGORY_ROLE_NAMES = ["Master", "Grandmaster", "Grandmaster (Black Role)"]

    # ----- actually check -----
    # categories
    for point_index, point_value in enumerate([500, 1000, 2000]) :
        for i, category in enumerate(hm.CATEGORIES) :
            if old_categories[i] < point_value and new_categories[i] >= point_value :
                updates.append(UpdateMessage(
                    location="log",
                    message=(f"Congratulations to <@{user.discord_id}>! " +
                             f"You have unlocked {category} {CATEGORY_ROLE_NAMES[point_index]} ({point_value}+ points)")
                ))
    # tiers
    for i in range(1, 6) : # 1, 2, 3, 4, 5
        #if    oldt1s       < 500   and    newt1s        >= 500
        if old_tiers[i - 1] < i*500 and new_tiers[i - 1] >= i * 500 :
            updates.append(UpdateMessage(
                location="log",
                message=(
                    f"Congratulations to <@{user.discord_id}>! " +
                    f"You have unlocked Tier {i} Enthusiast ({i * 500} points in Tier {i} completed games)."
                )
            ))

    return updates


async def user_update(user : CEUser, site_data : CEUser, database_name : list[CEGame]) -> tuple[list[UpdateMessage], CEUser] :
    """Takes in a user and updates it, and returns a list of things to send."""
    updates : list[UpdateMessage] = []

    original_points = user.get_total_points()
    original_completed_games = user.get_completed_games_2(database_name)
    original_rank = user.get_rank()
    original_games = user.owned_games

    user.owned_games = site_data.owned_games

    new_points = user.get_total_points()
    new_completed_games = user.get_completed_games_2(database_name)
    new_rank = user.get_rank()
    new_games = user.owned_games

    # get the role messages
    updates.append(check_category_roles(original_games, new_games, database_name, user))

    # search for newly completed games
    for game in new_completed_games :

        # if game is too low anyway, skip it
        TIER_MINIMUM = 4
        """int: The minimum tier for a game to be reported."""
        
        if not game.get_tier_num() >= TIER_MINIMUM : continue

        # check to see if it was completed before
        for old_game in original_completed_games :
            # it was completed before, so skip this
            if game.ce_id == old_game.ce_id : 
                continue
        
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
    for index, roll in enumerate(user.current_rolls) :
        # step 0: check multistage rolls
        # if the roll is multi stage AND its not in the final stage...
        # note: skip this if we're in the final stage because
        #       if it's in its final stage we can finish it out,
        #       this if statement just preps for the next one.
        if roll.is_multi_stage() and not roll.in_final_stage() and (await roll.is_won()) :
            # if we've already hit this roll before, keep moving
            if roll.due_time == None : continue

            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    f"<@{user.discord_id}>, you've finished your current stage in {roll.roll_name}. " +
                    f"To roll your next stage, type `/solo-roll {roll.roll_name}` in <#{hm.CASINO_ID}>."
                )
            ))

            # and kill the due time
            roll.due_time = None

        elif roll.is_won() :
            # add the update message
            updates.append(UpdateMessage(
                location="log",
                message=(
                    await roll.get_win_message()
                )
            ))
            # set the completed time to now
            roll.completed_time = hm.get_unix("now")

            # add the object to completed rolls, and
            # remove it from current
            user.add_completed_roll(roll)
            del user.current_rolls[index]
        
        elif roll.is_expired() :
            # add the update message
            updates.append(UpdateMessage(
                location="casino",
                message=(
                    await roll.get_fail_message()
                )
            ))
            
            # remove this roll from current rolls
            del user.current_rolls[index]