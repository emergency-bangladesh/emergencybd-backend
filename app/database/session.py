from sqlmodel import Session

from .engine import emr_engine


async def get_database_session():
    with Session(emr_engine) as session:
        yield session
