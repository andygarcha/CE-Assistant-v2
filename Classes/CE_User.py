import datetime
import json
from typing import get_args
import requests
from Classes.CE_Cooldown import CECooldown
from Classes.CE_Roll import CERoll
from Classes.CE_Game import CEGame
from Classes.CE_User_Game import CEUserGame
import Modules.hm as hm
from Classes.OtherClasses import CRData


class CEUser:
    """Class for the Challenge Enthusiast user."""
    def __init__(self, 
                 discord_id : int, 
                 ce_id : str, 
                 owned_games : list[CEUserGame],
                 rolls : list[CERoll],
                 display_name : str,
                 avatar : str):
        self._discord_id : int = discord_id
        self._ce_id : str = ce_id
        self._owned_games : list[CEUserGame] = owned_games
        self._rolls : list[CERoll] = rolls
        self._display_name = display_name
        self._avatar = avatar

    # ------------ getters -------------

    @property
    def display_name(self) :
        "Returns the display name of this user."
        return self._display_name
    
    def set_display_name(self, display_name : str) :
        "Setter."
        self._display_name = display_name
        pass
    
    @property
    def avatar(self) :
        "Returns the avatar of this user."
        return self._avatar

    def set_avatar(self, avatar : str) :
        "Setter."
        self._avatar = avatar
        pass

    @property
    def ce_id(self) :
        """Returns the Challenge Enthusiasts ID associated with this user."""
        return self._ce_id
    
    @property
    def discord_id(self) :
        """Returns the Discord ID associated with this user."""
        return self._discord_id
    
    def mention(self) :
        "Returns the Discord ID with brackets (Example: '<@1234>')."
        return f"<@{self.discord_id}>"
    
    @property
    def casino_score(self) :
        """Returns the casino score associated with this user."""
        return NotImplemented

    def get_total_points(self):
        """Returns the total amount of points this user has."""
        total_points : int = 0
        for game in self._owned_games:
            total_points += game.get_user_points()
        return total_points
    
    def get_rank(self) -> str :
        """Returns the current rank for this user."""
        total_points = self.get_total_points()
        if total_points >= 10000 : return "EX Rank"
        elif total_points >= 7500 : return "SSS Rank"
        elif total_points >= 5000 : return "SS Rank"
        elif total_points >= 2500 : return "S Rank"
        elif total_points >= 1000 : return "A Rank"
        elif total_points >= 500 : return "B Rank"
        elif total_points >= 250 : return "C Rank"
        elif total_points >= 50 : return "D Rank"
        else : return "E Rank"

    def rank_num(self) -> int :
        "Returns the rank as a user. E Rank is 0, D Rank is 1, etc."
        match(self.get_rank()) :
            case "E Rank" : return 0
            case "D Rank" : return 1
            case "C Rank" : return 2
            case "B Rank" : return 3
            case "A Rank" : return 4
            case "S Rank" : return 5
            case "SS Rank" : return 6
            case "SSS Rank" : return 7
            case "EX Rank" : return 8
        return None

    @property
    def owned_games(self):
        """Returns a list of :class:`CEUserGame`s that this user owns."""
        return self._owned_games
    
    def get_owned_game(self, ce_id : str) -> CEUserGame | None :
        """Returns the :class:`CEUserGame` object associated 
        `ce_id`, or `None` if this user doesn't own it."""
        for game in self.owned_games :
            if game.ce_id == ce_id : return game
        return None

    def owned_games_as_cegames(self, database_name : list[CEGame]) -> list[CEGame] :
        "Returns a list of this user's owned games as `CEGame`s."
        o : list[CEGame] = []
        for game in database_name :
            for owned_game in self.owned_games :
                if game.ce_id == owned_game.ce_id :
                    o.append(game)
        return o

    def get_completed_games(self) -> list[CEUserGame] :
        """Returns a list of :class:`CEUserGame`'s that this user has completed.
        This is so fucking inefficient. Please don't use this."""
        completed_games : list[CEUserGame] = []

        for game in self._owned_games :
            if game.get_regular_game().get_total_points() == game.get_user_points() : 
                completed_games.append(game)
        
        return completed_games
    
    def get_completed_games_2(self, database_name : list[CEGame]) -> list[CEGame] :
        """Returns a list of :class:`CEGame`'s that this user has completed."""
        completed_games : list[CEGame] = []
        for game in database_name :
            for user_game in self.owned_games :
                if game.ce_id == user_game.ce_id and game.get_total_points() == user_game.get_user_points() :
                    completed_games.append(game)
        return completed_games
    
    def get_objective(self, objective_id : str) :
        "Takes in an ID and returns the CEUserObjective associated with it."
        for game in self.owned_games :
            for objective in game.user_objectives :
                if objective_id == objective.ce_id : return objective

        return None
    
    def get_cr(self, database_name : list[CEGame]) -> CRData :
        "Returns the CR class."
        return CRData(owned_games=self.owned_games, database_name=database_name)
    
    @property
    def rolls(self) -> list[CERoll] :
        "Returns an array of `CERoll`s."
        return self._rolls
    
    @property
    def current_rolls(self) -> list[CERoll] :
        """Returns an array of :class:`CERoll`'s 
        that this user is currently participating in."""
        return [roll for roll in self.rolls if roll.status == "current"]

    @property
    def completed_rolls(self) -> list[CERoll] :
        """Returns an array of :class:`CERoll`'s
        that this user has previously completed."""
        return [roll for roll in self.rolls if roll.status == "won"]
    
    @property
    def pending_rolls(self) -> list[CERoll] :
        """Returns an array of :class:`CECooldown`'s
        that this user stores in their Pending Rolls section."""
        return [roll for roll in self.rolls if roll.status == "pending"]
    
    @property
    def failed_rolls(self) -> list[CERoll] :
        return [roll for roll in self.rolls if roll.status == "failed"]
    
    @property
    def past_rolls(self) -> list[CERoll] :
        return [roll for roll in self.rolls if (roll.status == "won" or roll.status == "failed")]
    

    # ----------- setters -----------

    @discord_id.setter
    def discord_id(self, input : int) -> None :
        """Sets this object's Discord ID according to `input`."""
        self._discord_id = input

    @owned_games.setter
    def owned_games(self, games) :
        """Sets the 'owned games' to `games`."""
        self._owned_games = games

    # == rolls cooldowns and pendings ==

    def add_current_roll(self, roll : CERoll) -> None :
        """Adds `roll` to this user's Current Rolls section."""
        roll.status = "current"
        self._rolls.append(roll)
    
    def add_completed_roll(self, roll : CERoll) -> None :
        """Adds `roll` to this user's Completed Rolls section."""
        roll.status = "won"
        self._rolls.append(roll)

    def add_pending(self, event_name : hm.ALL_ROLL_EVENT_NAMES) -> None :
        """Adds `pending` to this user's Pending section."""
        self._rolls.append(CERoll(
            roll_name=event_name,
            user_ce_id=self.ce_id,
            games=[""],
            status="pending",
            init_time=hm.get_unix("now"),
            due_time=hm.get_unix(minutes=10)
        ))

    def remove_current_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> None :
        "Removes `roll_name` from this user."
        for i, roll in enumerate(self.rolls) :
            if roll.roll_name == roll_name and roll.status == "current" : 
                del self._rolls[i]
                return
    
    def remove_pending(self, pending : hm.ALL_ROLL_EVENT_NAMES) :
        "Removes the pending from this user."
        for i, p in enumerate(self.rolls) :
            if p.roll_name == pending and p.status == "pending" :
                del self._rolls[i]
                break

    def remove_completed_rolls(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) :
        "Removes all completed rolls associated with roll_name."
        for i, roll in enumerate(self.rolls) :
            if roll.roll_name == roll_name and roll.status == "won" :
                del self._rolls[i]

    def remove_failed_rolls(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) :
        "removes all failed rolls associated with roll_name."
        for i, roll in enumerate(self.rolls) :
            if roll.roll_name == roll_name and roll.status == "failed" :
                del self._rolls[i]

    def clear_cooldowns(self) :
        "Removes all cooldowns."
        return NotImplemented

    # ----------- other methods ------------

    # -- rolls --
    def replace_current_roll(self, roll : CERoll) -> bool :
        "Replaces the user's roll with a new one. Returns true if it works, false if not."
        for i, event in enumerate(self.rolls) :
            if event.roll_name == roll.roll_name and event.status == "current" :
                self._rolls[i] = roll
                return True
        self.add_current_roll(roll)
        return False

    def has_completed_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user has completed `roll_name`."""
        for event in self.completed_rolls :
            if event.roll_name == roll_name : return True
        return False
    
    def get_completed_rolls(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> list[CERoll] :
        """Returns the `CERoll` associated with `roll_name`."""
        r = []
        for event in self.completed_rolls :
            if event.roll_name == roll_name : r.append(event)
        if len(r) != 0 : return r
        return None
    
    def has_current_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user is currently working on `roll_name`."""
        for event in self.current_rolls :
            if event.roll_name == roll_name : return True
        return False
    
    def get_current_roll(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> CERoll | None :
        "REturns the `CERoll` associated with `roll_name`."
        for event in self.current_rolls :
            if event.roll_name == roll_name : return event
        return None
    
    def has_cooldown(self, roll_name : hm.ALL_ROLL_EVENT_NAMES, database_name : list[CEGame]) -> bool :
        """Returns true if this user is currently on cooldown for `roll_name`."""
        # check infinite time rolls
        for roll in self.current_rolls :
            if roll.roll_name == roll_name :
                if roll.ends() : break
                cooldown_date = roll.calculate_cooldown_date(database_name)
                return cooldown_date is not None and cooldown_date > hm.get_unix("now")

        for roll in self.failed_rolls :
            if roll.roll_name == roll_name : 
                cooldown_date = roll.calculate_cooldown_date(database_name)
                if cooldown_date is not None and cooldown_date > hm.get_unix("now") : return True
        return False
    
    def get_cooldown_time(self, roll_name : hm.ALL_ROLL_EVENT_NAMES, database_name : list[CEGame]) -> int :
        """Returns the unix timestamp of the date `roll_name`'s cooldown ends
        (or `None` if not applicable.)"""
        # check infinite time rolls
        for roll in self.current_rolls :
            if roll.roll_name == roll_name :
                if roll.ends() : break
                return roll.calculate_cooldown_date(database_name)
            
        for roll in self.failed_rolls :
            if roll.roll_name == roll_name : 
                cooldown_date = roll.calculate_cooldown_date(database_name)
                if cooldown_date is not None and cooldown_date > hm.get_unix("now") : return cooldown_date
        return None
    
    def has_pending(self, roll_name : hm.ALL_ROLL_EVENT_NAMES) -> bool :
        """Returns true if this user is currently on pending for `roll_name`."""
        for pending in self.pending_rolls :
            if pending.roll_name == roll_name : return True
        return False
    
    def get_ce_rolls(self) -> list[CERoll] :
        "Returns a list of CERolls pulled from CE."

        # set the constant
        CE_GAME_ID = "76574ec1-42df-4488-a511-b9f2d9290e5d"

        # get the game, and if it's None, return
        ce_game = self.get_owned_game(CE_GAME_ID)
        if ce_game is None : return []

        # iterate through the objectives
        rolls : list[CERoll] = []
        for objective in ce_game.user_objectives :

            # if the objective name is a roll name, add it to the list.
            if objective.name in get_args(hm.ALL_ROLL_EVENT_NAMES) :
                rolls.append(CERoll(
                    roll_name=objective.name,
                    user_ce_id=self.ce_id,
                    games=None,
                    partner_ce_id=None,
                    init_time=None,
                    due_time=None,
                    completed_time=None,
                    rerolls=None
                ))

        # return the list.
        return rolls
    
    # -- game ownership and completion --

    def has_completed_game(self, game_id : str , database_name : list[CEGame]) :
        "Returns true if this user has completed this game, returns false otherwise."
        for user_game in self.owned_games :
            if user_game.ce_id == game_id :
                for game in database_name :
                    if game.ce_id == user_game.ce_id : return game.get_total_points() == user_game.get_user_points()
        return False

    def owns_game(self, game_id : str) -> bool :
        """Returns true if this user owns the game with 
        Challenge Enthusiast ID `game_id`."""
        for game in self.owned_games :
            if game.ce_id == game_id : return True
        return False
    
    def has_points(self, game_id : str) -> bool :
        """Returns true if this user has points in this game."""
        for game in self.owned_games :
            if game.ce_id == game_id : return game.get_user_points() != 0
        return False
    
    # -- other -- 

    def get_ce_link(self) -> str :
        "Returns the link to this user's Challenge Enthusiasts page."
        return f"https://cedb.me/user/{self.ce_id}"
    
    def get_api_user(self) -> 'CEAPIUser' :
        "Returns the CEAPIUser."
        data = requests.get(f'https://cedb.me/api/user/{self.ce_id}/')
        data = json.loads(data.text)

        return CEAPIUser(
            discord_id=self.discord_id,
            ce_id=self.ce_id,
            casino_score=self.casino_score,
            owned_games=self.owned_games,
            current_rolls=self.current_rolls,
            completed_rolls=self.completed_rolls,
            pending_rolls=self.pending_rolls,
            cooldowns=self.cooldowns,
            full_data=data,
            display_name=self.display_name,
            avatar=self.avatar
        )
        
    def completions(self, database_name : list[CEGame]) -> int :
        "Returns the number of completions this user has."
        completions = 0
        for owned_game in self.owned_games :
            if owned_game.is_completed(database_name=database_name) :
                completions += 1
        return completions

    

    def to_dict(self) -> dict :
        """Returns this user as a dictionary as used in the MongoDB database."""
        owned_games_array : list[dict] = []
        for game in self.owned_games :
            owned_games_array.append(game.to_dict())
        rolls_array = [roll.to_dict() for roll in self.rolls]

        user_dict = {
            "ce_id" : self.ce_id,
            "discord_id" : self.discord_id,
            "owned_games" : owned_games_array,
            "rolls" : rolls_array,
            "display-name" : self.display_name,
            "avatar" : self.avatar
        }

        return user_dict
    
    def __str__(self) :
        "Returns the string representation about this CEUser."

        owned_games_array : list[dict] = []
        for game in self.owned_games :
            owned_games_array.append(game.to_dict())
        current_rolls_array : list[CERoll] = []
        for roll in self.current_rolls :
            current_rolls_array.append(roll.to_dict())
        completed_rolls_array : list[CERoll] = []
        for roll in self.completed_rolls :
            completed_rolls_array.append(roll.to_dict())
        pendings_array : list[CECooldown] = []
        for pending in self.pending_rolls :
            pendings_array.append(pending.to_dict())

        return (
            "-- CEUser --" +
            "\nCE ID: " + self.ce_id +
            "\nDiscord ID: " + str(self.discord_id) +
            "\nCasino Score: " + str(self.casino_score) +
            "\nOwned Games: " + str(owned_games_array) +
            "\nCurrent Rolls: " + str(current_rolls_array) +
            "\nCompleted Rolls: " + str(completed_rolls_array) +
            "\nPendings: " + str(pendings_array)
        )
    
class CEAPIUser(CEUser) :
    "A user that's been pulled from the Challenge Enthusiasts API."
    def __init__(
            self,
            discord_id : int,
            ce_id : str,
            owned_games : list[CEUserGame],
            rolls : list[CERoll],
            full_data,
            display_name : str,
            avatar : str):
        super().__init__(discord_id, ce_id, owned_games, rolls, 
                          display_name, avatar)
        self.__full_data = full_data

    @property
    def full_data(self) :
        "Return the full API data."
        return self.__full_data
    
    @property
    def is_admin(self) -> bool :
        "Returns true if this user is an admin."
        return self.full_data['isAdmin']
    
    @property
    def api_user_objectives(self) -> list :
        "Returns the list of api user objectives as a list."
        return self.full_data['userObjectives']
    
    @property
    def api_user_games(self) -> list :
        "Returns the list of api games as a list."
        return self.full_data['userGames']
    
    @property
    def api_tier_summary(self) -> list :
        return self.full_data['userTierSummaries']
    
    def most_recent_objectives(self) :
        "Returns a list of `CEObjective`s."

        # make a constant
        NUM_OF_OBJECTIVES = 3

        # imports
        from Classes.CE_User_Objective import CEUserObjective
        from Modules import CEAPIReader

        # grab all the data
        ce_ids : list[str] = []
        completion_dates : list[int] = []
        game_names : list[str] = []
        for objective in self.full_data['userObjectives'] :
            ce_ids.append(objective['objective']['id'])
            completion_dates.append(CEAPIReader._timestamp_to_unix(objective['updatedAt']))
            game_names.append(objective['objective']['game']['name'])
        
        # make sure they didn't request too much
        if NUM_OF_OBJECTIVES > len(ce_ids) : return None

        # sort and shear them to the number requested
        ordered_pairs = sorted(zip(completion_dates, ce_ids, game_names), reverse=True)[0:NUM_OF_OBJECTIVES]

        # now get the objects and zip them with the completion dates
        objective_tuples : list[tuple[CEUserObjective | str, int, str]] = []
        for pair in ordered_pairs :
            objective_object = self.get_objective(pair[1])
            objective_tuples.append(
                ((objective_object if objective_object is not None else pair[1]),
                pair[0],
                pair[2])
            )
            

        return objective_tuples
    
    def most_recent_objectives_str(self) -> str :
        "Returns the string for the most recent objectives."
        
        # pull the data
        objective_tuples = self.most_recent_objectives()
        if objective_tuples is None : return "Error. Please try again or ping andy."

        # set up return
        return_str : str = ""

        # loop!
        for item in objective_tuples :
            # pull the actual items from the tuple
            objective = item[0]
            completion_unix = item[1]
            game_name = item[2]

            if type(objective) is str :
                return_str += f"Error, please ping andy. obj: {objective} game: {game_name}\n"
                continue

            # add to the return string
            return_str += (
                f"{objective.name} ({objective.user_points} {hm.get_emoji('Points')}) " +
                f"- [{game_name}](https://cedb.me/game/{objective.game_ce_id}/)\n"
            )

        return return_str
    
    def monthly_report_str(self) -> str :
        "Returns a string report of the points this user has gained in the last two months."
        curr_month_points = 0
        prev_month_points = 0

        now = datetime.datetime.now()
        current_month_datetime = datetime.datetime(year=now.year, month=now.month, day=1)
        previous_month_datetime = datetime.datetime(
            year=(now.year if now.month != 1 else now.year-1),
            month=(now.month - 1 if now.month != 1 else 12),
            day=1
        )

        for api_objective in self.api_user_objectives :
            if hm.cetimestamp_to_datetime(api_objective['updatedAt']) >= current_month_datetime :
                if api_objective['partial'] : curr_month_points += api_objective['objective']['pointsPartial']
                else : curr_month_points += api_objective['objective']['points']
            elif hm.cetimestamp_to_datetime(api_objective['updatedAt']) >= previous_month_datetime :
                if api_objective['partial'] : prev_month_points += api_objective['objective']['pointsPartial']
                else : prev_month_points += api_objective['objective']['points']

        return (
            f"Points this month ({hm.current_month_str()}): {curr_month_points} {hm.get_emoji('Points')}\n" + 
            f"Points last month ({hm.previous_month_str()}): {prev_month_points} {hm.get_emoji('Points')}"
        )
    
    def tier_genre_summary_str(self) -> str :
        "Returns a string report of the Tier and Genre Summary string to be sent."
        t1s, t2s, t3s, t4s, t5s = (0,)*5
        genre_dict : dict[str, int] = {}

        # get the data
        for tier in self.api_tier_summary :
            if hm.genre_id_to_name(tier['genreId']) == "Total" :
                t1s = tier['tier1']
                t2s = tier['tier2']
                t3s = tier['tier3']
                t4s = tier['tier4']
                t5s = tier['tier5']
                total = tier['total']
                continue
            genre_name = hm.genre_id_to_name(tier['genreId'])
            genre_dict[genre_name] = tier['total']
        
        # yeah
        LINE_BREAK_LIMIT = 3

        # set up categories
        return_str = ""
        i = 0
        for i, genre_name in enumerate(genre_dict) :
            # syntax
            if i % LINE_BREAK_LIMIT == 0 : return_str += "\n"

            # add the actual emoji and value
            return_str += f"{hm.get_emoji(genre_name)}: {genre_dict[genre_name]}\t"
        
        # set up tiers
        return_str += "\n"
        return_str += f"{hm.get_emoji('Tier 1')}: {t1s}\t{hm.get_emoji('Tier 2')}: {t2s}\t{hm.get_emoji('Tier 3')}: {t3s} \n"
        return_str += f"{hm.get_emoji('Tier 4')}: {t4s}\t{hm.get_emoji('Tier 5')}: {t5s}\tTotal: {total}"

        # and now return.
        return return_str