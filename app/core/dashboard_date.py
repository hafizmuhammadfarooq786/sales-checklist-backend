"""Dashboard date helpers for start/end range filtering."""

from datetime import date, datetime, time
from typing import Optional, Tuple


def get_dashboard_date_range(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Tuple[datetime, datetime, date, date]:
    """
    Resolve dashboard filter window in UTC (naive, matching DB timestamps).

    Defaults: start = first day of current month, end = today (UTC).

    Returns (range_start_dt, range_end_dt, resolved_start_date, resolved_end_date).
    """
    today = datetime.utcnow().date()
    resolved_end = end_date or today
    resolved_start = start_date or resolved_end.replace(day=1)

    if resolved_start > resolved_end:
        resolved_start = resolved_end.replace(day=1)

    range_start = datetime.combine(resolved_start, time.min)
    range_end = datetime.combine(
        resolved_end,
        time(23, 59, 59, 999999),
    )
    return range_start, range_end, resolved_start, resolved_end
