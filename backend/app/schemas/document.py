
from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    message: str
    school_id: int
    school_name: str
    pdf_filename: str
    chunks_created: int
    embeddings_created: int
