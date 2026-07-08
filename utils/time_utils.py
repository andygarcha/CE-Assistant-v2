import calendar
import datetime


def months_to_days(num_months: int) -> int:
    """Takes in a number of months `num_months` and returns
    the number of days between today and `num_months` months away.
    \nWritten by Schmole (thank you schmole!!)"""
    # purpose -- determine number of days to 'x' months away.
    # Required as duration will be different depending on
    # point in the year, and get_rollable_game requires day inputs
    # function input = number of months
    # function output = number of days between now and input months away
    if num_months == 0:
        return 0
    now = datetime.datetime.now(datetime.UTC)
    end_year = now.year + (now.month + num_months - 1) // 12
    end_month = (now.month + num_months - 1) % 12 + 1
    end_date = datetime.date(
        end_year, end_month, min(calendar.monthrange(end_year, end_month)[1], now.day)
    )
    date_delta = end_date - datetime.date(now.year, now.month, now.day)

    return date_delta.days


def get_datetime(
    days: int | str = 0, minutes=None, months=None, old_datetime=None
) -> datetime.datetime:
    """Returns a datetime object for `days` days (or `minutes` minutes, or `months` months) from the current time.
    \nAdditionally, `old_datetime` can be passed as a parameter to get `days` days (or `minutes` minutes, or `months` months) from that datetime."""
    # normalize string old_datetime to datetime
    if isinstance(old_datetime, str):
        try:
            old_datetime = datetime.datetime.fromisoformat(old_datetime)
        except Exception:
            try:
                old_datetime = cetimestamp_to_datetime(old_datetime)
            except Exception:
                old_datetime = None

    # -- old datetime passed --
    if old_datetime is not None:
        # ensure timezone-aware
        if old_datetime.tzinfo is None:
            old_datetime = old_datetime.replace(tzinfo=datetime.UTC)
        if isinstance(days, str):
            raise ValueError(f"old_datetime not None and days is a str. {days=}")

        if minutes is not None:
            return old_datetime + datetime.timedelta(minutes=minutes)
        if months is not None:
            return old_datetime + datetime.timedelta(days=months_to_days(months))
        return old_datetime + datetime.timedelta(days=days)

    # -- old datetime NOT passed --
    # return right now
    if days == "now":
        return datetime.datetime.now(datetime.UTC)
    # return the minutes
    if minutes is not None:
        return datetime.datetime.now(datetime.UTC) + datetime.timedelta(minutes=minutes)
    # return the months
    if months is not None:
        return get_datetime(days=months_to_days(months))
    # return the days
    if days is None:
        return None
    if isinstance(days, str):
        raise ValueError(f"days is a str but not = 'now'. {days=}")

    return datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=days)


def get_unix(days=0, minutes=None, months=None, old_unix=None) -> int:
    """Deprecated: Use get_datetime() instead. Returns a unix timestamp."""
    old_dt = None
    if isinstance(old_unix, int):
        old_dt = datetime.datetime.fromtimestamp(old_unix, datetime.UTC)
    dt = get_datetime(days, minutes, months, old_dt)
    return int(dt.timestamp())


def current_month_str() -> str:
    "Returns the name of the current month."
    return datetime.datetime.now(datetime.UTC).strftime("%B")


def current_month_num() -> int:
    "The number of the current month."
    return datetime.datetime.now(datetime.UTC).month


def current_year_num() -> int:
    return datetime.datetime.now(datetime.UTC).year


def previous_month_str() -> str:
    "Returns the name of the previous month."
    current_month_num = datetime.datetime.now(datetime.UTC).month
    previous_month_num = (current_month_num - 1) if current_month_num != 1 else 12
    return datetime.datetime(
        year=2024, month=previous_month_num, day=1, tzinfo=datetime.UTC
    ).strftime("%B")


def cetimestamp_to_datetime(timestamp: str) -> datetime.datetime:
    "Takes in a CE timestamp (UTC, trailing 'Z') and returns a UTC-aware datetime."
    naive = datetime.datetime.strptime(  # noqa: DTZ007 -- converted to UTC-aware on the next line
        str(timestamp[:-5:]), "%Y-%m-%dT%H:%M:%S"
    )
    return naive.replace(tzinfo=datetime.UTC)
