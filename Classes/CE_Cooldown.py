import Modules.hm as hm
class CECooldown :
    """An object that represents a Challenge Enthusiast roll cooldown."""
    def __init__(self,
                 roll_name : hm.ALL_ROLL_EVENT_NAMES,
                 end_time : int) :
        self._roll_name = roll_name
        self._end_time = end_time

    # ---------- getters ----------

    @property
    def roll_name(self) -> str :
        """Returns the event name for this cooldown."""
        return self._roll_name
    
    @property
    def end_time(self) -> int :
        """Returns the end time for this cooldown as a unix timestamp."""
        return self._end_time
    
    # ----------- other methods ---------

    def is_expired(self) -> bool :
        """Returns true if this cooldown is ready to be lifted."""
        return self.end_time < hm.get_unix("now")
    
    def to_dict(self) -> dict :
        """Returns this object as a dictionary."""
        return {
            'Event Name' : self.roll_name,
            'End Time' : self.end_time
        }
    
    def __str__(self) :
        "Returns the string representation of this CECooldown."
        return (
            "-- CECooldown --" +
            "\nCooldown Name: " + self.roll_name +
            "\nEnd Time: " + self.end_time
        )