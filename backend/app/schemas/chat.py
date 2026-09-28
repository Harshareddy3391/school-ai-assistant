from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str


class ChatSource(BaseModel):
    document_id: int
    page_number: int | None = None
    school_id: int
    rerank_score: float | None = None


class ChatResponse(BaseModel):
    question: str
    answer: str
    school_id: int | None = None
    school_name: str | None = None
    sources: list[ChatSource] = []