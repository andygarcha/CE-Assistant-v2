def get_item_from_list(ce_id, list) :
    """Return the object who's Challenge Enthusiast
    ID is provided by `ce_id`."""
    for item in list :
        if item.ce_id == ce_id : return item
    return None

def get_index_from_list(ce_id, list) :
    """Returns the index of the object provided by `ce_id`."""
    for i in range(len(list)) :
        if list[i].ce_id == ce_id : return i
    return -1

def replace_item_in_list(ce_id, item, list) -> list :
    """Replaces the object who's Challenge Enthusiast
    ID is provided by `ce_id`."""
    for i in range(len(list)) :
        if list[i].ce_id == ce_id :
            list[i] = item
    return list


def get_grammar_str(input : list) -> str :
    """Takes in the list `input` and returns a string of their
    contents grammatically correct.\n
    Example: [a, b, c] --> 'a, b, and c'\n
    Example: [a] --> 'a'"""
    #TODO: finish this function
    return NotImplemented

def format_ce_link(ce_link : str) -> str | None :
    "Takes in a full link and returns the CE ID."

    # replace all the other stuff
    ce_id = ce_link.replace("https://","").replace("www.","").replace("cedb.me", "").replace("/","").replace("games","").replace("user","")

    # if it's not valid, return None
    if not (ce_id[8:9] == ce_id[13:14] == ce_id[18:19] == ce_id[23:24] == "-") :
        return None
    
    # else, return the id.
    return ce_id

def is_within_percentage(input : int | float, percentage : int, value : int) -> bool :
    """Checks if `input` is within `percent`% of `value`.
    Example: `is_within_percentage(10, 50, 15)` will check if 10 is within 50% of 15."""
    threshold = percentage / 100 * value
    lower_bound = value - threshold
    upper_bound = value + threshold
    return lower_bound <= input <= upper_bound