from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    filename: str
    file_path: str
    document_type: str | None = None


class DocumentCreate(DocumentBase):
    school_id: int


class DocumentResponse(DocumentBase):
    id: int
    school_id: int
    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )