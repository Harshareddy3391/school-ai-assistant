from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.embedding_service import generate_embedding
from app.services.school_service import resolve_school
from app.rag.hybrid_search import hybrid_search
from app.rag.reranker import rerank_chunks
from app.rag.context_builder import build_context
from app.rag.generator import generate_answer

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    # 1. Resolve school from user question
    school = resolve_school(
        db=db,
        question=request.question
    )

    # 2. School not found
    if school is None:
        return ChatResponse(
            question=request.question,
            answer="I couldn't identify the school from your question. Please mention the school name.",
            school_id=None,
            school_name=None,
            sources=[]
        )

    school_id = school.id

    # 3. Generate query embedding
    query_embedding = generate_embedding(request.question)

    # 4. Hybrid search only inside this school
    hybrid_results = hybrid_search(
        db=db,
        query=request.question,
        query_embedding=query_embedding,
        school_id=school_id,
        top_k=5
    )

    if not hybrid_results:
        return ChatResponse(
            question=request.question,
            answer="I couldn't find this information in the school's documents.",
            school_id=school.id,
            school_name=school.name,
            sources=[]
        )

    # 5. Reranking
    reranked_results = rerank_chunks(
        query=request.question,
        chunks=hybrid_results,
        top_k=3
    )

    # 6. Build context
    context = build_context(
        chunks=reranked_results,
        max_chunks=3
    )

    # 7. Generate answer
    answer = generate_answer(
        question=request.question,
        context=context
    )

    # 8. Sources
    sources = [
        ChatSource(
            document_id=chunk["document_id"],
            page_number=chunk.get("page_number"),
            school_id=chunk["school_id"],
            rerank_score=chunk.get("rerank_score")
        )
        for chunk in reranked_results
    ]

    # 9. Response
    return ChatResponse(
        question=request.question,
        answer=answer,
        school_id=school.id,
        school_name=school.name,
        sources=sources
    )