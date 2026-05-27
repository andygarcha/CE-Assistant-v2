import datetime


from utils.time_utils import (
    cetimestamp_to_datetime,
    get_datetime,
    months_to_days,
)

FIXED_DT = datetime.datetime(2024, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)


# ── months_to_days ────────────────────────────────────────────────────────────


class TestMonthsToDays:
    def test_zero_months(self):
        assert months_to_days(0) == 0

    def test_one_month_in_valid_range(self):
        # Any single month spans 28-31 days
        assert 28 <= months_to_days(1) <= 31

    def test_twelve_months_in_valid_range(self):
        # A year is 365 or 366 days
        assert 365 <= months_to_days(12) <= 366

    def test_two_months_at_least_56_days(self):
        assert months_to_days(2) >= 56

    def test_result_is_int(self):
        assert isinstance(months_to_days(3), int)


# ── cetimestamp_to_datetime ───────────────────────────────────────────────────


class TestCETimestampToDatetime:
    def test_parses_standard_timestamp(self):
        result = cetimestamp_to_datetime("2024-01-15T12:30:45.000Z")
        assert result == datetime.datetime(2024, 1, 15, 12, 30, 45)

    def test_parses_midnight(self):
        result = cetimestamp_to_datetime("2023-12-31T00:00:00.000Z")
        assert result == datetime.datetime(2023, 12, 31, 0, 0, 0)

    def test_fractional_seconds_ignored(self):
        # Only the .000 part (5 chars) is stripped — fractional digits don't bleed through
        result = cetimestamp_to_datetime("2024-06-01T08:15:30.999Z")
        assert result == datetime.datetime(2024, 6, 1, 8, 15, 30)

    def test_returns_datetime_object(self):
        result = cetimestamp_to_datetime("2024-03-20T18:45:00.000Z")
        assert isinstance(result, datetime.datetime)


# ── get_datetime ──────────────────────────────────────────────────────────────


class TestGetDatetime:
    def test_none_days_returns_none(self):
        assert get_datetime(days=None) is None

    def test_now_returns_timezone_aware(self):
        result = get_datetime(days="now")
        assert result.tzinfo is not None

    def test_days_offset_from_old_datetime(self):
        result = get_datetime(days=10, old_datetime=FIXED_DT)
        assert result == FIXED_DT + datetime.timedelta(days=10)

    def test_negative_days_offset(self):
        result = get_datetime(days=-5, old_datetime=FIXED_DT)
        assert result == FIXED_DT + datetime.timedelta(days=-5)

    def test_minutes_offset_from_old_datetime(self):
        result = get_datetime(minutes=90, old_datetime=FIXED_DT)
        assert result == FIXED_DT + datetime.timedelta(minutes=90)

    def test_minutes_takes_priority_over_days_with_old_datetime(self):
        # minutes kwarg wins when both are non-None
        result = get_datetime(days=99, minutes=30, old_datetime=FIXED_DT)
        assert result == FIXED_DT + datetime.timedelta(minutes=30)

    def test_string_old_datetime_parsed(self):
        result = get_datetime(days=1, old_datetime="2024-06-15T12:00:00")
        expected_base = datetime.datetime(2024, 6, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
        assert result == expected_base + datetime.timedelta(days=1)

    def test_zero_days_from_now_is_recent(self):
        before = datetime.datetime.now(datetime.timezone.utc)
        result = get_datetime(days=0)
        after = datetime.datetime.now(datetime.timezone.utc)
        assert before <= result <= after

    def test_future_days_from_now(self):
        before = datetime.datetime.now(datetime.timezone.utc)
        result = get_datetime(days=7)
        expected_approx = before + datetime.timedelta(days=7)
        delta = abs((result - expected_approx).total_seconds())
        assert delta < 2  # within 2 seconds of expected

    def test_minutes_from_now(self):
        before = datetime.datetime.now(datetime.timezone.utc)
        result = get_datetime(minutes=60)
        expected_approx = before + datetime.timedelta(minutes=60)
        delta = abs((result - expected_approx).total_seconds())
        assert delta < 2
