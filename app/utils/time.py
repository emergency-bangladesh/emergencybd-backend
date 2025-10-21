from datetime import datetime, timezone


def get_utc_time() -> datetime:
    return datetime.now(tz=timezone.utc)
