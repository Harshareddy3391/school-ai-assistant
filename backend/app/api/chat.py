from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource

from app.services.embedding_service import generate_embedding
from app.services.school_service import resolve_school

from app.rag.query_rewriter import rewrite_query
from app.rag.hybrid_search import hybrid_search
from app.rag.reranker import rerank_chunks
from app.rag.context_builder import build_context
from app.rag.generator import generate_answer


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    # 1. Try to identify a specific school.
    #    If no school is mentioned, we will search all school PDFs.
    school = resolve_school(
        db=db,
        question=request.question
    )

    school_id = school.id if school else None

    # 2. Rewrite the user's question for better retrieval
    rewritten_query = rewrite_query(
        request.question
    )

    # 3. Generate embedding from the rewritten query
    query_embedding = generate_embedding(
        rewritten_query
    )

    # 4. Hybrid search
    #
    # If school_id exists:
    #     Search only that school's document chunks.
    #
    # If school_id is None:
    #     Search ALL school document chunks.
    hybrid_results = hybrid_search(
        db=db,
        query=rewritten_query,
        query_embedding=query_embedding,
        school_id=school_id,
        top_k=10
    )

    # 5. No relevant information found
    if not hybrid_results:
        return ChatResponse(
            question=request.question,
            answer=(
                "I couldn't find this information in the available "
                "school documents."
            ),
            school_id=school_id,
            school_name=school.name if school else None,
            sources=[]
        )

    # 6. Reranking
    reranked_results = rerank_chunks(
        query=rewritten_query,
        chunks=hybrid_results,
        top_k=5
    )

    # 7. Build context
    context = build_context(
        chunks=reranked_results,
        max_chunks=5
    )

    # Debug information
    print("\n========== SCHOOL ==========")

    if school:
        print("School ID:", school.id)
        print("School Name:", school.name)
    else:
        print("No specific school identified")
        print("Searching ALL school PDFs")

    print("\n========== REWRITTEN QUERY ==========")
    print(rewritten_query)

    print("\n========== RERANKED RESULTS ==========")

    for chunk in reranked_results:
        print("School ID:", chunk.get("school_id"))
        print("Document ID:", chunk.get("document_id"))
        print("Page:", chunk.get("page_number"))
        print("Score:", chunk.get("rerank_score"))
        print("Content:")
        print(chunk.get("content"))
        print("-" * 80)

    print("\n========== FINAL CONTEXT ==========")
    print(context)

    print("=" * 80)

    # 8. Generate answer using the ORIGINAL user question
    answer = generate_answer(
        question=request.question,
        context=context
    )

    # 9. Build sources
    sources = [
        ChatSource(
            document_id=chunk["document_id"],
            page_number=chunk.get("page_number"),
            school_id=chunk["school_id"],
            rerank_score=chunk.get("rerank_score")
        )
        for chunk in reranked_results
    ]

    # 10. Return response
    return ChatResponse(
        question=request.question,
        answer=answer,
        school_id=school_id,
        school_name=school.name if school else None,
        sources=sources
    )