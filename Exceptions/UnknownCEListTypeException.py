class UnknownCEListTypeException(Exception) :
    """An exception for CE Assistant v2 to denote
    a `CEList` containing unknown values.."""
    def __init__(self, message : str) :
        self._message = message
    
    def get_message(self) -> str :
        """Returns the message associated with this exception."""
        return self._message