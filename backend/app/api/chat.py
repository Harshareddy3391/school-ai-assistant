from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session


from app.core.database import get_db
from app.serfrom fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.embedding_service import generate_embedding
from app.rag.hybrid_search import hybrid_search
from app.rag.reranker import rerank_chunks
from app.rag.context_builder import build_context
from app.rag.generator import generate_answer


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


class ChatRequest(BaseModel):
    question: str
    school_id: int


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[dict]


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    # 1. Generate query embedding
    query_embedding = generate_embedding(
        request.question
    )

    # 2. Hybrid retrieval
    hybrid_results = hybrid_search(
        db=db,
        query=request.question,
        query_embedding=query_embedding,
        school_id=request.school_id,
        top_k=5
    )

    if not hybrid_results:
        return ChatResponse(
            question=request.question,
            answer=(
                "I couldn't find this information "
                "in the school's documents."
            ),
            sources=[]
        )

    # 3. Reranking
    reranked_results = rerank_chunks(
        query=request.question,
        chunks=hybrid_results,
        top_k=3
    )

    # 4. Build context
    context = build_context(
        chunks=reranked_results,
        max_chunks=3
    )

    # 5. Generate answer
    answer = generate_answer(
        question=request.question,
        context=context
    )

    # 6. Prepare sources
    sources = [
        {
            "document_id": chunk.get("document_id"),
            "page_number": chunk.get("page_number"),
            "school_id": chunk.get("school_id"),
            "rerank_score": chunk.get("rerank_score")
        }
        for chunk in reranked_results
    ]

    return ChatResponse(
        question=request.question,
        answer=answer,
        sources=sources
    )