"""Timezone utilities for consistent timestamp handling"""

from datetime import datetime, timedelta, timezone
from typing import Optional

# EST/EDT timezone (UTC-5 or UTC-4 during daylight saving)
EST = timezone(timedelta(hours=-5))
EDT = timezone(timedelta(hours=-4))


def get_current_datetime() -> datetime:
    """Get current datetime in EST/EDT timezone

    Returns:
        Current datetime in Eastern timezone
    """
    # For simplicity, using EST (UTC-5)
    # In production, would use pytz or zoneinfo for proper DST handling
    return datetime.now(EST)


def get_utc_now() -> datetime:
    """Get current UTC datetime

    Returns:
        Current datetime in UTC
    """
    return datetime.now(timezone.utc)


def to_est(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert datetime to EST timezone

    Args:
        dt: Datetime to convert (assumes UTC if no timezone)

    Returns:
        Datetime in EST or None if input is None
    """
    if dt is None:
        return None

    # If naive datetime, assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(EST)


def format_datetime(dt: Optional[datetime], include_time: bool = True) -> str:
    """Format datetime for display

    Args:
        dt: Datetime to format
        include_time: Whether to include time in output

    Returns:
        Formatted string or empty string if None
    """
    if dt is None:
        return ""

    # Convert to EST for display
    dt_est = to_est(dt)

    if include_time:
        return dt_est.strftime("%Y-%m-%d %I:%M %p EST")
    return dt_est.strftime("%Y-%m-%d")


def parse_datetime(date_str: str) -> Optional[datetime]:
    """Parse datetime string

    Args:
        date_str: DateTime string to parse

    Returns:
        Datetime object or None if parsing fails
    """
    if not date_str:
        return None

    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Assume EST timezone if not specified
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=EST)
            return dt
        except ValueError:
            continue

    return None
