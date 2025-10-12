from sqlmodel import SQLModel

from .engine import emr_engine
from .models import *  # noqa


def create_database():
    SQLModel.metadata.create_all(bind=emr_engine)
