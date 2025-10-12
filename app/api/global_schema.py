from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    message: str
    data: T | None = None
