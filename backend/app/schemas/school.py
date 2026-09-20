from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SchoolBase(BaseModel):
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None


class SchoolCreate(SchoolBase):
    pass


class SchoolResponse(SchoolBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )