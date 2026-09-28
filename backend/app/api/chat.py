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
from app.services.school_list_service import get_schools_by_city
from app.services.intent_router import detect_intent, Intent

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


# ============================================================
# CHAT ENDPOINT
# ============================================================

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


    # ========================================================
    # 2. DETECT INTENT
    # ========================================================

    intent = detect_intent(
        request.question
    )

    print("\n========== INTENT ==========")
    print("Question:", request.question)
    print("Intent:", intent.value)


    print("\n========== SESSION ==========")
    print("Session ID:", request.session_id)
    print("Previous Messages:", len(history))


    # ========================================================
    # 3. BUILD CONVERSATION CONTEXT
    # ========================================================

    conversation_context = ""

    if history:

        conversation_parts = []

        for message in history:

            conversation_parts.append(
                f"{message['role'].upper()}: "
                f"{message['content']}"
            )

        conversation_context = "\n".join(
            conversation_parts
        )


    print(
        "\n========== CONVERSATION HISTORY =========="
    )

    if conversation_context:

        print(conversation_context)

    else:

        print("No previous conversation")


    # ========================================================
    # 4. TRY TO IDENTIFY SPECIFIC SCHOOL
    # ========================================================

    school = resolve_school(
        db=db,
        question=request.question
    )

    school_id = (
        school.id
        if school
        else None
    )

    school_name = (
        school.name
        if school
        else None
    )


        # ========================================================
    # 5. BUILD QUERY FOR REWRITING
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
    # 6. QUERY REWRITING
    # ========================================================

    rewritten_query = rewrite_query(
        rewrite_input
    )

    print(
        "\n========== REWRITTEN QUERY =========="
    )

    print(rewritten_query)


    # ========================================================
    # 7. GENERATE QUERY EMBEDDING
    # ========================================================

    query_embedding = generate_embedding(
        rewritten_query
    )


    # ========================================================
    # 8. SQL + RAG / NORMAL RAG
    # ========================================================

    if intent == Intent.SQL_AND_RAG:

        print(
            "\n========== SQL + RAG ROUTE =========="
        )

        # ---------------------------------------------
        # Find city from question
        # ---------------------------------------------

        cities = (
            db.query(School.city)
            .filter(
                School.city.isnot(None)
            )
            .distinct()
            .all()
        )

        question_lower = (
            request.question.lower()
        )

        detected_city = None

        for city_row in cities:

            city = city_row[0]

            if (
                city
                and city.lower()
                in question_lower
            ):

                detected_city = city

                break


        # ---------------------------------------------
        # Get schools using SQL
        # ---------------------------------------------

        if detected_city:

            schools = get_schools_by_city(
                db=db,
                city=detected_city
            )

        else:

            schools = (
                db.query(School)
                .order_by(School.name)
                .all()
            )


        # ---------------------------------------------
        # Get school IDs
        # ---------------------------------------------

        sql_school_ids = [
            school_item.id
            for school_item in schools
        ]


        print(
            "\n========== SQL SCHOOL IDS =========="
        )

        print(sql_school_ids)


        # ---------------------------------------------
        # RAG only for SQL-selected schools
        # ---------------------------------------------

        if sql_school_ids:

            hybrid_results = hybrid_search(
                db=db,
                query=rewritten_query,
                query_embedding=query_embedding,
                school_ids=sql_school_ids,
                top_k=10
            )

        else:

            hybrid_results = []


    else:

        print(
            "\n========== RAG ROUTE =========="
        )

        # ---------------------------------------------
        # Normal RAG
        #
        # Specific school → that school
        # No school → all schools
        # ---------------------------------------------

        hybrid_results = hybrid_search(
            db=db,
            query=rewritten_query,
            query_embedding=query_embedding,
            school_id=school_id,
            top_k=10
        )




            # ========================================================
    # 9. NO RESULTS
    # ========================================================

    if not hybrid_results:

        llm_response = (
            "I couldn't find this information in the "
            "available school documents."
        )


        _save_conversation(
            request.session_id,
            request.question,
            llm_response
        )


        return ChatResponse(
            question=request.question,
            rag_results=[],
            llm_response=llm_response,
            school_id=school_id,
            school_name=school_name,
            sources=[]
        )


    # ========================================================
    # 10. RERANKING
    # ========================================================

    reranked_results = rerank_chunks(
        query=rewritten_query,
        chunks=hybrid_results,
        top_k=5
    )


    # ========================================================
    # 11. BUILD RAG CONTEXT
    # ========================================================

    context = build_context(
        chunks=reranked_results,
        max_chunks=5
    )


    # ========================================================
    # 12. DEBUG INFORMATION
    # ========================================================

    print(
        "\n========== SCHOOL =========="
    )

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
            "Searching selected/all school PDFs"
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
    # 13. GENERATE LLM RESPONSE
    # ========================================================

    llm_response = generate_answer(
        question=request.question,
        context=context
    )



        # ========================================================
    # 14. BUILD RAG RESULTS
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
    # 15. BUILD SOURCES
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
    # 16. SAVE CURRENT CONVERSATION
    # ========================================================

    _save_conversation(
        request.session_id,
        request.question,
        llm_response
    )


    # ========================================================
    # 17. FINAL RESPONSE
    # ========================================================

    return ChatResponse(
        question=request.question,

        # Actual information retrieved from PDFs
        rag_results=rag_results,

        # AI generated response
        llm_response=llm_response,

        school_id=school_id,

        school_name=school_name,

        sources=sources
    )


# ============================================================
# SAVE TEMPORARY CONVERSATION
# ============================================================

def _save_conversation(
    session_id: str,
    question: str,
    answer: str
):

    conversation_memory.setdefault(
        session_id,
        []
    )


    conversation_memory[
        session_id
    ].append(
        {
            "role": "user",
            "content": question
        }
    )


    conversation_memory[
        session_id
    ].append(
        {
            "role": "assistant",
            "content": answer
        }
    )


    # Keep latest 10 messages

    conversation_memory[
        session_id
    ] = conversation_memory[
        session_id
    ][-10:]