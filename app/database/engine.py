from sqlite3 import Connection as SQLite3Connection
from sqlite3 import Cursor as SQLite3Cursor
from typing import Any

from sqlalchemy import event
from sqlmodel import create_engine

from ..core.config import config

emr_engine = create_engine(config.database_uri)


@event.listens_for(emr_engine, "connect")
def set_pragmas(dbapi_connection: SQLite3Connection, connection_record: Any):
    cursor: SQLite3Cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.close()
