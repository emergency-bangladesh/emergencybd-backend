from asgi2wsgi import ASGI2WSGI

from app import app as fastapi_app

application = ASGI2WSGI(fastapi_app)
