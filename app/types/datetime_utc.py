from datetime import datetime, timezone

from sqlalchemy.engine import Dialect
from sqlalchemy.types import DateTime as SQLAlchemyDateTime
from sqlalchemy.types import TypeDecorator


class SQLAlchemyDateTimeUTC(TypeDecorator[datetime]):
    impl = SQLAlchemyDateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is not None and hasattr(value, "tzinfo") and value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
