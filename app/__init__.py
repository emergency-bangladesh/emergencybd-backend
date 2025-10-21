import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.auth.routes import router as auth_router
from .api.file_upload.routes import router as file_upload_router
from .api.image.routes import router as image_router
from .api.issue.routes import router as issue_router
from .api.team.routes import router as team_router
from .api.validate.routes import router as validate_router
from .api.volunteer.routes import router as volunteer_router
from .database import create_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="Emergency Bangladesh Rest API",
    version="0.1.0",
    summary="Comprehensive backend services for the EmergencyBD platform, enabling rapid response and information sharing during emergencies.",
    description="""This API provides core functionalities for the EmergencyBD application, including emergency contact management, resource allocation, and real-time updates. It aims to connect individuals in need with available help efficiently. Our project's source code is available on [GitHub](https://github.com/emergency-bangladesh).""",
    contact={
        "name": "Emergency Bangladesh",
        "url": "https://www.emergencybd.com",
        "email": "project.emergencybd@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    docs_url="/documentation",
    redoc_url="/redocumentation",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://emergencybd.com",
        "https://www.emergencybd.com",
        "https://manage.emergencybd.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.info(
        f"HTTPException for {request.method} {request.url.path}: status_code={exc.status_code}, detail={exc.detail}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.info(
        f"RequestValidationError for {request.method} {request.url.path}: {exc.errors()}"
    )
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception for {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )


create_database()

for router in [
    auth_router,
    file_upload_router,
    image_router,
    issue_router,
    team_router,
    validate_router,
    volunteer_router,
]:
    app.include_router(router)


@app.get("/")
async def read_root(request: Request) -> dict[str, str | dict[str, str]]:
    base_url = str(request.base_url).rstrip("/")
    docs_link = f"{base_url}{app.docs_url}"
    redoc_link = f"{base_url}{app.redoc_url}"
    openapi_link = f"{base_url}{app.openapi_url}"

    return {
        "message": "Welcome to EmergencyBD Backend API!",
        "documentation_links": {
            "swagger_ui": docs_link,
            "redoc": redoc_link,
            "openapi_spec": openapi_link,
        },
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
