from datetime import UTC, datetime, timedelta

INCLUDE_HISTORY = True


def find_last_downtime():
    now_utc = datetime.now(UTC)
    downtime_today_utc = datetime(
        now_utc.year, now_utc.month, now_utc.day, 11, 5, 0, 0, UTC
    )
    if now_utc <= downtime_today_utc:
        last_downtime = downtime_today_utc - timedelta(days=1)
    else:
        last_downtime = downtime_today_utc
    return last_downtime.timestamp()


LAST_DOWNTIME = find_last_downtime()
