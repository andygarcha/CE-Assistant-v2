from CE_Game import CE_Game

class CE_Roll:
    """Roll event."""
    def __init__(self,
                 roll_name,
                 init_time,
                 due_time,
                 completed_time,
                 games,
                 partner_ce_id,
                 cooldown_days,
                 rerolls):
        self._roll_name : str = roll_name
        self._init_time : int = init_time
        self._due_time : int = due_time
        self._completed_time : int = completed_time
        self._games : CE_Game = games
        self._partner_ce_id : str = partner_ce_id
        self._cooldown_days : int = cooldown_days
        self._rerolls : int = rerolls