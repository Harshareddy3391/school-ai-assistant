
from pydantic import BaseModel


class SchoolResponse(BaseModel):
    id: int
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
