from CE_Roll import CE_Roll
from CE_Game import CE_Game
from CE_User_Game import CE_User_Game

class CE_User:
    """Class for the Challenge Enthusiast user."""
    def __init__(self, 
                 discord_id : int, 
                 ce_id : str, 
                 casino_score : int, 
                 owned_games : list[CE_User_Game],
                 current_rolls : list[CE_Roll], 
                 completed_rolls : list[CE_Roll], 
                 pending_rolls : list[CE_Roll], 
                 cooldowns : list[CE_Roll]):
        self._discord_id : int = discord_id
        self._ce_id : str = ce_id
        self._casino_score : int = casino_score
        self._owned_games : list[CE_User_Game] = owned_games
        self._current_rolls : list[CE_Roll] = current_rolls
        self._completed_rolls : list[CE_Roll] = completed_rolls
        self._pending_rolls : list[CE_Roll] = pending_rolls
        self._cooldowns : list[CE_Roll] = cooldowns

    # ------------ getters -------------

    def get_ce_id(self) :
        """Returns the Challenge Enthusiasts ID associated with this user."""
        return self._ce_id
    
    def get_discord_id(self) :
        """Returns the Discord ID associated with this user."""
        return self._discord_id
    
    def get_casino_score(self) :
        """Returns the casino score associated with this user."""
        return self._casino_score

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

    def get_owned_games(self):
        """Returns a list of :class:`CE_User_Game`s that this user owns."""
        return self._owned_games

    def get_completed_games(self) -> list[CE_User_Game] :
        """Returns a list of :class:`CE_User_Game`s that this user has completed."""
        completed_games : list[CE_User_Game] = []

        for game in self._owned_games :
            if game.get_total_points() == game.get_user_points() : completed_games.append(game)
        
        return completed_games
    

    # ----------- other methods ------------
    
    def to_dict(self) -> dict :
        """Returns this user as a dictionary as used in the MongoDB database."""
        owned_games_array : list[dict] = []
        for game in self.get_owned_games() :
            owned_games_array.append(game.to_dict())

        user_dict = {
            self.get_ce_id : {
                "CE ID" : self.get_ce_id(),
                "Discord ID" : self.get_discord_id(),
                "Casino Score" : self.get_casino_score(),
                "Owned Games" : owned_games_array
            }
        }

        return user_dict