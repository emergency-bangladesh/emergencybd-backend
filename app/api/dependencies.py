from typing import Annotated

from fastapi import Depends
from sqlmodel import Session

from ..database.models.account import Account, Admin, User
from ..database.models.volunteer import Volunteer
from ..database.session import get_database_session
from ..services.auth import (
    get_current_admin,
    get_current_user,
    get_current_volunteer,
    get_logged_in_account,
    get_requesting_actor,
)

DatabaseSession = Annotated[Session, Depends(get_database_session)]
LoggedInAccount = Annotated[Account, Depends(get_logged_in_account)]
CurrentAdmin = Annotated[Admin, Depends(get_current_admin)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentVolunteer = Annotated[Volunteer, Depends(get_current_volunteer)]
RequestingActor = Annotated[Account | Admin, Depends(get_requesting_actor)]
