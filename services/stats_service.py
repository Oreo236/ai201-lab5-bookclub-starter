"""
services/stats_service.py — BookClub

Computes reading statistics for a user: streak, books finished this month,
and total pages read.
"""

from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo
from services import reading_service


def _coerce_timezone(user_timezone: str | tzinfo) -> tzinfo:
    if isinstance(user_timezone, str):
        return ZoneInfo(user_timezone)
    return user_timezone


def _as_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def calculate_streak(
    user_id: str,
    user_timezone: str | tzinfo = timezone.utc,
    today: date | None = None,
) -> int:
    """
    Calculate a user's current reading streak in consecutive days.

    A streak is the number of consecutive calendar days on which the user
    finished at least one book, counting back from today (or yesterday, if
    nothing has been finished today yet).

    Returns 0 if the user has no reading history or if there is a gap of
    more than one day since their most recent finished book.

    Args:
        user_id: ID of the user.
        user_timezone: Timezone used to convert UTC finish timestamps into the
            user's local calendar dates.
        today: User-local date to count back from. Defaults to the current date
            in user_timezone.

    Returns:
        The streak count as an integer.
    """
    events = reading_service.get_reading_history(user_id)
    if not events:
        return 0

    local_timezone = _coerce_timezone(user_timezone)

    # Collect unique reading dates, most recent first.
    dates = sorted(
        set(_as_utc(e.finished_at).astimezone(local_timezone).date() for e in events),
        reverse=True,
    )

    if today is None:
        today = datetime.now(local_timezone).date()

    # Streak must start from today or yesterday — otherwise it has already broken.
    if (today - dates[0]).days > 1:
        return 0

    streak = 1
    for i in range(len(dates) - 1):
        delta = (dates[i] - dates[i + 1]).days
        if delta == 1:
            streak += 1
        else:
            break

    return streak


def books_this_month(user_id: str) -> int:
    """
    Count the number of books the user finished in the current calendar month.

    Args:
        user_id: ID of the user.

    Returns:
        Count of books finished this month.
    """
    events = reading_service.get_reading_history(user_id)
    today = date.today()
    return sum(
        1
        for e in events
        if e.finished_at.year == today.year and e.finished_at.month == today.month
    )


def total_pages_read(user_id: str) -> int:
    """
    Sum the page counts of all books the user has finished.

    Args:
        user_id: ID of the user.

    Returns:
        Total pages read as an integer.
    """
    events = reading_service.get_reading_history(user_id)
    return sum(e.book.pages for e in events)
