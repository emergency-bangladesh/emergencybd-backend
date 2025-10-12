from .auth.routes import router as auth_router
from .file_upload.routes import router as file_upload_router
from .image.routes import router as image_router
from .issue.routes import router as issue_router
from .team.routes import router as team_router
from .validate.routes import router as validate_router
from .volunteer.routes import router as volunteer_router

__all__ = [
    "auth_router",
    "file_upload_router",
    "image_router",
    "issue_router",
    "team_router",
    "validate_router",
    "volunteer_router",
]
