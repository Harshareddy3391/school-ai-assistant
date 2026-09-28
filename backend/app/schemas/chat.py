from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: str


class RAGResult(BaseModel):
    school_id: int
    school_name: str | None = None
    document_id: int
    page_number: int | None = None
    content: str

    vector_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float | None = None
    rerank_score: float | None = None


class ChatSource(BaseModel):
    document_id: int
    page_number: int | None = None
    school_id: int
    rerank_score: float | None = None


class ChatResponse(BaseModel):
    question: str

    rag_results: list[RAGResult] = []

    llm_response: str

    school_id: int | None = None
    school_name: str | None = None

    sources: list[ChatSource] = []