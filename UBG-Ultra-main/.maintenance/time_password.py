#!/usr/bin/env python3

import datetime
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

MELBOURNE_TZ = ZoneInfo("Australia/Melbourne")

# Monday=1, Tuesday=2, Wednesday=3, Thursday=4, Friday=5, Saturday=6, Sunday=7
DAY_MAP = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7}


def generate(now=None):
    if now is None:
        now = datetime.datetime.now(MELBOURNE_TZ)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=MELBOURNE_TZ)
    else:
        now = now.astimezone(MELBOURNE_TZ)

    hour = now.hour % 12
    if hour == 0:
        hour = 12
    minutes = now.minute
    day = DAY_MAP[now.weekday()]

    base = f"{hour}{minutes:02d}{day}"
    rev = base[::-1]

    secs_left = 60 - now.second
    if secs_left == 60:
        secs_left = 60

    clock = f"{now.hour:02d}:{now.minute:02d}:{now.second:02d} {now.strftime('%A')} (AEST/AEDT)"

    return {"base": base, "reversed": rev, "clock": clock,
            "secsLeft": secs_left}


def password_for(ts=None):
    if ts is None:
        return generate()
    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    return generate(dt.astimezone(MELBOURNE_TZ))