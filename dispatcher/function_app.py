"""Timer that asks GitHub to run the "Refresh brackets" workflow.

GitHub's own cron is often late (or slow to start for a new schedule), so this
Azure Function is the punctual trigger. It wakes every 5 minutes and decides,
from the tournament calendar below, whether this slot should dispatch.
"""
import datetime as dt
import json
import logging
import os
import urllib.error
import urllib.request

import azure.functions as func

app = func.FunctionApp()

REPO = os.environ.get("GITHUB_REPO", "rwsanders/nchvc-nationals")
WORKFLOW = os.environ.get("GITHUB_WORKFLOW", "refresh.yml")

# All times UTC (Central = UTC-5 in October)
TOURNAMENT_START = dt.datetime(2026, 10, 15, 11, 0, tzinfo=dt.timezone.utc)  # Thu 6 AM CT
TOURNAMENT_END = dt.datetime(2026, 10, 18, 6, 0, tzinfo=dt.timezone.utc)     # Sun 1 AM CT
HOURLY_UNTIL = dt.datetime(2026, 10, 19, 0, 0, tzinfo=dt.timezone.utc)


def should_dispatch(now: dt.datetime) -> str | None:
    """Return a reason to dispatch for this 5-minute slot, or None to skip."""
    if TOURNAMENT_START <= now < TOURNAMENT_END:
        return "tournament: every 5 minutes"
    first_slot_of_hour = 5 <= now.minute < 10  # one slot per hour, a few minutes past
    if now < HOURLY_UNTIL:
        return "hourly" if first_slot_of_hour else None
    return "daily" if now.hour == 12 and first_slot_of_hour else None


def dispatch(token: str) -> int:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW}/dispatches",
        data=json.dumps({"ref": "main"}).encode(),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "nchvc-dispatcher",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status


SITE_DATA = os.environ.get("SITE_DATA_URL", "https://witty-ground-0124a1610.5.azurestaticapps.net/data.json")


def site_age_minutes() -> float | None:
    """How old the live site's data is, or None if it can't be read."""
    try:
        with urllib.request.urlopen(urllib.request.Request(SITE_DATA, headers={"User-Agent": "nchvc-dispatcher"}), timeout=20) as r:
            generated = json.load(r)["generated"]
        return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(generated)).total_seconds() / 60
    except Exception as e:  # noqa: BLE001
        logging.warning("could not read live data: %s", e)
        return None


@app.timer_trigger(schedule="0 */5 * * * *", arg_name="timer", run_on_startup=False, use_monitor=False)
def refresh_dispatch(timer: func.TimerRequest) -> None:
    now = dt.datetime.now(dt.timezone.utc)
    reason = should_dispatch(now)
    if not reason and TOURNAMENT_START <= now < TOURNAMENT_END:
        # self-heal: a skipped or failed run shouldn't leave parents looking at old scores
        age = site_age_minutes()
        if age is not None and age > 15:
            reason = f"live data is {age:.0f} min old"
            logging.warning("stale site data; dispatching early (%s)", reason)
    if not reason:
        return
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        logging.error("GITHUB_TOKEN app setting is missing; cannot dispatch")
        return
    try:
        status = dispatch(token)
        logging.info("dispatched %s (%s): HTTP %s", WORKFLOW, reason, status)
    except urllib.error.HTTPError as e:
        # 401/403: token expired or lacks Actions write; 404: wrong repo/workflow name
        logging.error("dispatch failed: HTTP %s %s", e.code, e.read()[:300])
