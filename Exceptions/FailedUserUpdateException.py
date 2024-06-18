class FailedUserUpdateException(Exception) :
    """An exception for CE Assistant v2 to denote
    an issue updating users from the Challenge Enthusiasts API."""
    def __init__(self, message : str) :
        self._message = message
    
    def get_message(self) -> str :
        """Returns the message associated with this exception."""
        return self._message