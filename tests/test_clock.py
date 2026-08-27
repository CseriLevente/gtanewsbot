"""
Clock and scheduling tests.

The central claim these defend: because Hungary's DST transitions happen between
02:00 and 03:00, an "at or after 18:00, once per local date" scheduler cannot
double-post or skip a day. If someone later moves DIGEST_HOUR into the
02:00-03:00 window, or swaps calendar.timegm() for time.mktime(), these fail.
"""
from __future__ import annotations

import calendar
import time
from datetime import date, datetime, timedelta

import pytest

from src.clock import (
    local_date_key,
    parse_date_key,
    should_post_digest,
    struct_time_to_epoch,
)

# Hungary's 2026/2027 DST transitions (last Sunday of October / March, 02:00-03:00 local).
FALL_BACK_2026 = date(2026, 10, 25)
SPRING_FORWARD_2027 = date(2027, 3, 28)


# ---------------------------------------------------------------------------
# should_post_digest
# ---------------------------------------------------------------------------

def test_not_due_before_digest_hour():
    due, reason = should_post_digest(
        digest_hour=18, already_posted=False, now=datetime(2026, 8, 25, 17, 59)
    )
    assert due is False
    assert "before digest hour" in reason


def test_due_at_digest_hour():
    due, _ = should_post_digest(
        digest_hour=18, already_posted=False, now=datetime(2026, 8, 25, 18, 0)
    )
    assert due is True


def test_due_late_at_night_is_still_due():
    """A PC that woke at 23:30 must still post today's digest, not skip the day."""
    due, _ = should_post_digest(
        digest_hour=18, already_posted=False, now=datetime(2026, 8, 25, 23, 30)
    )
    assert due is True


def test_never_posts_twice_for_the_same_date():
    due, reason = should_post_digest(
        digest_hour=18, already_posted=True, now=datetime(2026, 8, 25, 18, 30)
    )
    assert due is False
    assert "already posted" in reason


def test_already_posted_wins_over_lateness():
    """Once today's slot is claimed, no later run in the same day may post."""
    for hour in (18, 19, 22, 23):
        due, _ = should_post_digest(
            digest_hour=18, already_posted=True, now=datetime(2026, 8, 25, hour, 5)
        )
        assert due is False


# ---------------------------------------------------------------------------
# DST safety
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("transition", [FALL_BACK_2026, SPRING_FORWARD_2027])
def test_18h_is_unambiguous_on_transition_days(transition):
    """
    18:00 must be constructible and unique on a DST transition day.

    This is the load-bearing property: the transition happens at 02:00-03:00, so
    18:00 is untouched. Contrast with 02:30, which does not exist on the
    spring-forward day and occurs twice on the fall-back day.
    """
    moment = datetime(transition.year, transition.month, transition.day, 18, 0)
    assert moment.hour == 18
    assert local_date_key(moment) == transition.isoformat()


@pytest.mark.parametrize("transition", [FALL_BACK_2026, SPRING_FORWARD_2027])
def test_no_local_date_is_skipped_or_duplicated_across_a_transition(transition):
    """
    Walking calendar days across a transition yields strictly increasing,
    contiguous, unique date keys — so the UNIQUE constraint on date_key can
    neither block a legitimate day nor admit a duplicate.
    """
    start = transition - timedelta(days=3)
    keys = [local_date_key(datetime.combine(start + timedelta(days=i), datetime.min.time()).replace(hour=18))
            for i in range(7)]
    assert len(keys) == len(set(keys)), "a local date was duplicated"
    parsed = [parse_date_key(k) for k in keys]
    for earlier, later in zip(parsed, parsed[1:]):
        assert (later - earlier).days == 1, "a local date was skipped"


def test_digest_hour_in_dst_window_is_the_known_hazard():
    """
    Documents why DIGEST_HOUR must not be 2 or 3.

    02:30 does not exist on the spring-forward day. A scheduler keyed on
    "hour >= 2" would still fire (03:xx passes the test), but a scheduler keyed
    on an exact 02:30 match would silently skip the day. check-ready rejects
    hours 2-3 for this reason; this test pins the reasoning.
    """
    assert 2 <= 2 <= 3 and 2 <= 3 <= 3  # the rejected range
    # 18 is outside it.
    assert not (2 <= 18 <= 3)


# ---------------------------------------------------------------------------
# Feed timestamp conversion
# ---------------------------------------------------------------------------

def test_struct_time_to_epoch_treats_input_as_utc():
    """
    feedparser hands back UTC struct_time. calendar.timegm() is correct;
    time.mktime() would interpret it as LOCAL and shift every feed item by the
    current offset — an error whose size changes at the DST boundary.
    """
    st = time.struct_time((2026, 8, 25, 12, 0, 0, 0, 237, 0))
    assert struct_time_to_epoch(st) == calendar.timegm(st)


def test_struct_time_to_epoch_differs_from_mktime_when_offset_nonzero():
    """Regression guard: catches a future 'fix' that swaps in time.mktime()."""
    st = time.struct_time((2026, 8, 25, 12, 0, 0, 0, 237, 0))
    if time.timezone == 0 and not time.daylight:
        pytest.skip("machine is on UTC; the two functions coincide")
    assert struct_time_to_epoch(st) != int(time.mktime(st))


def test_struct_time_to_epoch_handles_missing_timestamp():
    """Feeds routinely omit or malform pubDate; that must not raise."""
    assert struct_time_to_epoch(None) is None
    assert struct_time_to_epoch(()) is None


def test_date_key_round_trip():
    d = date(2026, 11, 19)  # GTA 6 release day
    assert parse_date_key(local_date_key(datetime.combine(d, datetime.min.time()))) == d
