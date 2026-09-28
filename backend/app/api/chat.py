from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    RAGResult
)

from app.models.school import School

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


# ============================================================
# TEMPORARY CONVERSATION MEMORY
# ============================================================

conversation_memory: dict[str, list[dict[str, str]]] = {}


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    # ========================================================
    # 1. GET CURRENT CONVERSATION HISTORY
    # ========================================================

    history = conversation_memory.get(
        request.session_id,
        []
    )

    print("\n========== SESSION ==========")
    print("Session ID:", request.session_id)
    print("Previous Messages:", len(history))


    # ========================================================
    # 2. BUILD CONVERSATION CONTEXT
    # ========================================================

    conversation_context = ""

    if history:

        conversation_parts = []

        for message in history:

            conversation_parts.append(
                f"{message['role'].upper()}: {message['content']}"
            )

        conversation_context = "\n".join(
            conversation_parts
        )

    print("\n========== CONVERSATION HISTORY ==========")

    if conversation_context:
        print(conversation_context)
    else:
        print("No previous conversation")


    # ========================================================
    # 3. TRY TO IDENTIFY SPECIFIC SCHOOL
    # ========================================================

    school = resolve_school(
        db=db,
        question=request.question
    )

    school_id = school.id if school else None


    # ========================================================
    # 4. BUILD QUERY FOR REWRITING
    # ========================================================

    if conversation_context:

        rewrite_input = f"""
Previous conversation:

{conversation_context}

Current user question:

{request.question}
"""

    else:

        rewrite_input = request.question


    # ========================================================
    # 5. QUERY REWRITING
    # ========================================================

    rewritten_query = rewrite_query(
        rewrite_input
    )

    print("\n========== REWRITTEN QUERY ==========")
    print(rewritten_query)


    # ========================================================
    # 6. GENERATE QUERY EMBEDDING
    # ========================================================

    query_embedding = generate_embedding(
        rewritten_query
    )


    # ========================================================
    # 7. HYBRID SEARCH
    #
    # school_id exists:
    #     Search specific school
    #
    # school_id is None:
    #     Search ALL school PDFs
    # ========================================================

    hybrid_results = hybrid_search(
        db=db,
        query=rewritten_query,
        query_embedding=query_embedding,
        school_id=school_id,
        top_k=10
    )


    # ========================================================
    # 8. NO RESULTS
    # ========================================================

    if not hybrid_results:

        llm_response = (
            "I couldn't find this information in the "
            "available school documents."
        )

        # Save conversation
        conversation_memory.setdefault(
            request.session_id,
            []
        )

        conversation_memory[
            request.session_id
        ].append(
            {
                "role": "user",
                "content": request.question
            }
        )

        conversation_memory[
            request.session_id
        ].append(
            {
                "role": "assistant",
                "content": llm_response
            }
        )

        return ChatResponse(
            question=request.question,
            rag_results=[],
            llm_response=llm_response,
            school_id=school_id,
            school_name=(
                school.name
                if school
                else None
            ),
            sources=[]
        )


    # ========================================================
    # 9. RERANKING
    # ========================================================

    reranked_results = rerank_chunks(
        query=rewritten_query,
        chunks=hybrid_results,
        top_k=5
    )


    # ========================================================
    # 10. BUILD RAG CONTEXT
    # ========================================================

    context = build_context(
        chunks=reranked_results,
        max_chunks=5
    )


    # ========================================================
    # DEBUG INFORMATION
    # ========================================================

    print("\n========== SCHOOL ==========")

    if school:

        print(
            "School ID:",
            school.id
        )

        print(
            "School Name:",
            school.name
        )

    else:

        print(
            "No specific school identified"
        )

        print(
            "Searching ALL school PDFs"
        )


    print(
        "\n========== RERANKED RESULTS =========="
    )


    for chunk in reranked_results:

        print(
            "School ID:",
            chunk.get("school_id")
        )

        print(
            "Document ID:",
            chunk.get("document_id")
        )

        print(
            "Page:",
            chunk.get("page_number")
        )

        print(
            "Vector Score:",
            chunk.get("vector_score")
        )

        print(
            "Keyword Score:",
            chunk.get("keyword_score")
        )

        print(
            "Hybrid Score:",
            chunk.get("hybrid_score")
        )

        print(
            "Rerank Score:",
            chunk.get("rerank_score")
        )

        print("Content:")

        print(
            chunk.get("content")
        )

        print("-" * 80)


    print(
        "\n========== FINAL CONTEXT =========="
    )

    print(context)

    print("=" * 80)


    # ========================================================
    # 11. GENERATE LLM RESPONSE
    # ========================================================

    llm_response = generate_answer(
        question=request.question,
        context=context
    )


    # ========================================================
    # 12. BUILD RAG RESULTS
    # ========================================================

    rag_results = []

    for chunk in reranked_results:

        chunk_school = db.get(
            School,
            chunk["school_id"]
        )

        rag_results.append(
            RAGResult(
                school_id=chunk["school_id"],

                school_name=(
                    chunk_school.name
                    if chunk_school
                    else None
                ),

                document_id=chunk["document_id"],

                page_number=(
                    chunk.get("page_number")
                ),

                content=chunk["content"],

                vector_score=(
                    chunk.get("vector_score")
                ),

                keyword_score=(
                    chunk.get("keyword_score")
                ),

                hybrid_score=(
                    chunk.get("hybrid_score")
                ),

                rerank_score=(
                    chunk.get("rerank_score")
                )
            )
        )


    # ========================================================
    # 13. BUILD SOURCES
    # ========================================================

    sources = [

        ChatSource(
            document_id=chunk["document_id"],

            page_number=(
                chunk.get("page_number")
            ),

            school_id=chunk["school_id"],

            rerank_score=(
                chunk.get("rerank_score")
            )
        )

        for chunk in reranked_results

    ]


    # ========================================================
    # 14. SAVE CURRENT CONVERSATION
    # ========================================================

    conversation_memory.setdefault(
        request.session_id,
        []
    )


    conversation_memory[
        request.session_id
    ].append(
        {
            "role": "user",
            "content": request.question
        }
    )


    conversation_memory[
        request.session_id
    ].append(
        {
            "role": "assistant",
            "content": llm_response
        }
    )


    # ========================================================
    # 15. LIMIT TEMPORARY MEMORY
    # ========================================================

    # Keep only the latest 10 messages
    # to prevent the conversation context
    # from becoming too large.

    conversation_memory[
        request.session_id
    ] = conversation_memory[
        request.session_id
    ][-10:]


    # ========================================================
    # 16. FINAL RESPONSE
    # ========================================================

    return ChatResponse(

        question=request.question,

        # Actual information retrieved from PDFs
        rag_results=rag_results,

        # AI generated response
        llm_response=llm_response,

        school_id=school_id,

        school_name=(
            school.name
            if school
            else None
        ),

        sources=sources
    )