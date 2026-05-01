import calendar
import datetime
import time

def months_to_days(num_months : int) -> int:
    """Takes in a number of months `num_months` and returns 
    the number of days between today and `num_months` months away.
    \nWritten by Schmole (thank you schmole!!)"""
    # purpose -- determine number of days to 'x' months away. 
    #Required as duration will be different depending on 
    #point in the year, and get_rollable_game requires day inputs
    # function input = number of months
    # function output = number of days between now and input months away
    if num_months == 0 : return 0 
    now = datetime.datetime.now()
    end_year = now.year + (now.month + num_months - 1) // 12
    end_month = (now.month + num_months - 1) % 12 + 1
    end_date = datetime.date(end_year, end_month, min(calendar.monthrange(end_year, end_month)[1], now.day))
    date_delta = end_date - datetime.date(now.year, now.month, now.day)

    return date_delta.days


def get_datetime(days = 0, minutes = None, months = None, old_datetime = None) -> datetime.datetime:
    """Returns a datetime object for `days` days (or `minutes` minutes, or `months` months) from the current time.
    \nAdditionally, `old_datetime` can be passed as a parameter to get `days` days (or `minutes` minutes, or `months` months) from that datetime."""
    # -- old datetime passed --
    if(old_datetime != None) :
        if (minutes != None) : return old_datetime + datetime.timedelta(minutes=minutes)
        elif (months != None) : return old_datetime + datetime.timedelta(days=months_to_days(months))
        else : return old_datetime + datetime.timedelta(days=days)

    # -- old datetime NOT passed --
    # return right now
    if(days == "now") : return datetime.datetime.now(datetime.timezone.utc)
    # return the minutes
    elif (minutes != None) : return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
    # return the months
    elif (months != None) : return get_datetime(days=months_to_days(months))
    # return the days
    elif (days == None) : return None

    else: return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)


def get_unix(days = 0, minutes = None, months = None, old_unix = None) -> int:
    """Deprecated: Use get_datetime() instead. Returns a unix timestamp."""
    old_dt = None
    if isinstance(old_unix, int):
        old_dt = datetime.datetime.fromtimestamp(old_unix, datetime.timezone.utc)
    dt = get_datetime(days, minutes, months, old_dt)
    return int(dt.timestamp())


def current_month_str() -> str :
    "Returns the name of the current month."
    return datetime.datetime.now().strftime('%B')

def current_month_num() -> int :
    "The number of the current month."
    return datetime.datetime.now().month

def current_year_num() -> int:
    return datetime.datetime.now().year

def previous_month_str() -> str :
    "Returns the name of the previous month."
    current_month_num = datetime.datetime.now().month
    previous_month_num = (current_month_num - 1) if current_month_num != 1 else 12
    return datetime.datetime(year=2024, month=previous_month_num, day = 1).strftime('%B')


def cetimestamp_to_datetime(timestamp : str) -> datetime.datetime :
    "Takes in a CE timestamp and returns a datetime."
    return datetime.datetime.strptime(str(timestamp[:-5:]), "%Y-%m-%dT%H:%M:%S")