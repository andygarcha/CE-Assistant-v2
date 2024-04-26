from CE_Objective import CE_Objective

class CE_Objective_User(CE_Objective):
    """A class for an objective held by a user. Extends the :class:`CE_Objective` class."""
    def __init__(self,
                 ce_id : str,
                 is_community : bool,
                 description : str,
                 point_value : int,
                 name : str,
                 requirements : str,
                 achievement_ce_ids : list[str],
                 user_points : int,
                 point_value_partial : int = 0):
        super().__init__(ce_id,
                 is_community,
                 description,
                 point_value,
                 name,
                 requirements,
                 achievement_ce_ids,
                 point_value_partial)
        self._user_points = user_points
    
    def get_user_points(self) -> int :
        """Returns the number of points this user has for this objective."""
        return self._user_points
    
    # --------- other methods ---------
    def to_dict(self) -> dict :
        dict = {
            self.get_ce_id() : self.get_user_points()
        }
        return dict