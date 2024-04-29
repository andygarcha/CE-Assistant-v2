from CE_Roll import CERoll
import hm
class CECooldown :
    """An object that represents a Challenge Enthusiast roll cooldown."""
    def __init__(self,
                 roll_name : hm.roll_event_names,
                 end_time : int) :
        self._roll_name = roll_name
        self._end_time = end_time

    # ---------- getters ----------

    def get_roll_name(self) -> str :
        """Returns the event name for this cooldown."""
        return self._roll_name
    
    def get_end_time(self) -> int :
        """Returns the end time for this cooldown as a unix timestamp."""
        return self._end_time
    
    # ----------- other methods ---------

    def is_expired(self) -> bool :
        """Returns true if this cooldown is ready to be lifted."""
        return self.get_end_time() < hm.get_current_unix()