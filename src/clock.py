"""
The single clock.

This machine has NO tzdata: `zoneinfo.ZoneInfo("Europe/Budapest")` raises
ZoneInfoNotFoundError. The system local clock IS Budapest. So, exactly as in
tozsdeturbo-bot, local system time is the one and only clock. Do not add tzdata
and do not introduce ZoneInfo/pytz.

WHY 18:00 IS SAFE (this is the load-bearing argument, not a convenience)
-----------------------------------------------------------------------
Hungary's DST transitions occur between 02:00 and 03:00 local time. Therefore
18:00 local exists exactly once on every calendar day of the year, and no local
date is ever skipped or duplicated. A scheduler defined as

    "post once per local DATE, at or after 18:00 local"

backed by a UNIQUE constraint on the date, therefore CANNOT double-post and
CANNOT skip a day because of DST. If the digest hour were moved into the
02:00-03:00 window this reasoning collapses: the spring-forward hour does not
exist, and the autumn hour happens twice.

THE ACTUAL TIME BOMB
--------------------
`datetime.now().astimezone().utcoffset()` is +02:00 today (CEST) and becomes
+01:00 on 2026-10-25 (CET). Any hardcoded `timezone(timedelta(hours=2))` is a
bug with a due date. So:

  * naive local time is used ONLY for (a) the date key and (b) the `hour >= N`
    comparison — both are DST-safe as argued above;
  * every duration, ordering, age or TTL uses epoch seconds (`time.time()`),
    which is monotonic across DST transitions;
  * feed timestamps are converted with `calendar.timegm()` (feedparser's
    `published_parsed` is already UTC) and NEVER with `time.mktime()`, which
    interprets its argument as LOCAL time and would shift every feed item by
    the current UTC offset;
  * digest content is selected by an UNSENT FLAG, never by a "last N hours"
    window, so an ambiguous or missing local hour cannot drop or duplicate items.
"""
from __future__ import annotations

import calendar
import logging
import time
from datetime import date, datetime

logger = logging.getLogger(__name__)

# Expected local timezone characteristics for Budapest (CET/CEST).
# time.timezone is the offset WEST of UTC in seconds for standard time, so
# CET (UTC+1) is -3600. time.daylight is 1 when the platform knows about a DST
# rule for the local zone.
_EXPECTED_STD_OFFSET_SECONDS = -3600


def local_now() -> datetime:
    """Current local wall-clock time. The only entry point for 'now'."""
    return datetime.now()


def epoch_now() -> int:
    """Current UTC epoch seconds. Use this for ALL duration/age arithmetic."""
    return int(time.time())


def local_date_key(now: datetime | None = None) -> str:
    """
    The idempotency key for 'one digest per local day', as 'YYYY-MM-DD'.

    A string is returned deliberately: it goes straight into a SQLite UNIQUE
    column, and a text key cannot be accidentally arithmetic'd.
    """
    return (now or local_now()).date().isoformat()


def parse_date_key(key: str) -> date:
    """Inverse of local_date_key, for display and tests."""
    return date.fromisoformat(key)


def struct_time_to_epoch(parsed) -> int | None:
    """
    Convert feedparser's `published_parsed` / `updated_parsed` to epoch seconds.

    feedparser normalises feed timestamps to UTC and hands back a
    `time.struct_time`. `calendar.timegm()` treats that as UTC, which is
    correct. `time.mktime()` would treat it as LOCAL and shift every item by the
    current offset — an error that changes size at the DST boundary.
    """
    if not parsed:
        return None
    try:
        return int(calendar.timegm(parsed))
    except (TypeError, ValueError, OverflowError):
        return None


def should_post_digest(
    *,
    digest_hour: int,
    already_posted: bool,
    now: datetime | None = None,
) -> tuple[bool, str]:
    """
    Decide whether the daily digest should be posted right now.

    Pure function of (local hour, whether today's date key already exists) so it
    is directly unit-testable — including across DST transition dates.

    `already_posted` must come from a SELECT on the digest_runs UNIQUE date key,
    NOT from anything held in memory: the bot runs as a short-lived process every
    15 minutes and has no memory between runs. That constraint is deliberate —
    it forces the catch-up decision into SQLite where it can be tested.

    Returns (should_post, reason).
    """
    n = now or local_now()
    if already_posted:
        return False, f"digest for {local_date_key(n)} already posted"
    if n.hour < digest_hour:
        return False, f"local hour {n.hour:02d} is before digest hour {digest_hour:02d}"
    return True, f"due: local hour {n.hour:02d} >= {digest_hour:02d}, no run for {local_date_key(n)}"


def check_local_clock() -> tuple[bool, str]:
    """
    Startup sanity check that the local clock really is Central European.

    Deliberately numeric. `time.tzname` is LOCALISED — on this machine it reads
    'Közép-európai nyári idő', so any string match against 'CEST' fails. The
    numeric offset does not lie.

    Returns (ok, message). A False result is worth logging loudly but is not
    fatal: the bot still functions, it just may post at an unexpected hour.
    """
    std_offset = time.timezone
    if std_offset != _EXPECTED_STD_OFFSET_SECONDS:
        hours = -std_offset / 3600.0
        return False, (
            f"local standard-time offset is UTC{hours:+.1f}, expected UTC+1 "
            f"(Europe/Budapest). The digest will post at the configured local hour "
            f"of THIS machine's timezone, which may not be Hungarian local time."
        )
    if not time.daylight:
        return False, (
            "local timezone reports no DST rule; Hungary observes CEST. "
            "Digest timing will drift by an hour for part of the year."
        )
    return True, "local clock looks like Europe/Budapest (UTC+1 standard, DST rule present)"


def describe_now() -> str:
    """Human-readable clock summary for the CLI and for the digest footer."""
    n = local_now()
    off = n.astimezone().utcoffset()
    off_str = "unknown"
    if off is not None:
        total = int(off.total_seconds())
        off_str = f"UTC{total // 3600:+d}:{abs(total) % 3600 // 60:02d}"
    return f"{n.strftime('%Y-%m-%d %H:%M:%S')} local ({off_str})"
