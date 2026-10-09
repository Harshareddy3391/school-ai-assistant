from pydantic import BaseModel


class ChatRequest(BaseModel):
    question: str
    session_id: str


class SchoolInfo(BaseModel):
    id: int
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None


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

    # Type of response:
    # school_list
    # rag_answer
    # sql_and_rag
    # general
    response_type: str

    # Natural-language AI answer
    llm_response: str

    # Structured school information
    schools: list[SchoolInfo] = []

    # RAG results
    rag_results: list[RAGResult] = []

    # Selected school information
    school_id: int | None = None
    school_name: str | None = None

    # Sources
    sources: list[ChatSource] = []