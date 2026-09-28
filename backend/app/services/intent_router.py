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


# =========================================================
# TEMPORARY CONVERSATION MEMORY
# =========================================================

conversation_memory: dict[str, list[dict[str, str]]] = {}


# =========================================================
# CHAT ENDPOINT
# =========================================================

@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):

    # =====================================================
    # 1. GET SESSION HISTORY
    # =====================================================

    history = conversation_memory.get(
        request.session_id,
        []
    )

    print("\n" + "=" * 80)
    print("SESSION")
    print("=" * 80)

    print("Session ID:", request.session_id)
    print("Previous Messages:", len(history))


    # =====================================================
    # 2. DETECT INTENT
    # =====================================================

    intent = detect_intent(
        request.question
    )

    print("\n" + "=" * 80)
    print("INTENT")
    print("=" * 80)

    print("Question:", request.question)
    print("Intent:", intent.value)


    # =====================================================
    # 3. BUILD CONVERSATION CONTEXT
    # =====================================================

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


    print("\n" + "=" * 80)
    print("CONVERSATION HISTORY")
    print("=" * 80)

    if conversation_context:

        print(
            conversation_context
        )

    else:

        print(
            "No previous conversation"
        )


    # =====================================================
    # 4. RESOLVE SCHOOL
    # =====================================================

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


    print("\n" + "=" * 80)
    print("SCHOOL RESOLUTION")
    print("=" * 80)

    if school:

        print("School ID:", school.id)
        print("School Name:", school.name)

    else:

        print(
            "No specific school identified"
        )


    # =====================================================
    # 5. SQL ROUTE
    # =====================================================

    if intent == Intent.SQL:

        print("\n" + "=" * 80)
        print("SQL ROUTE")
        print("=" * 80)

        # ---------------------------------------------
        # Try to identify city
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

            if city and city.lower() in question_lower:

                detected_city = city

                break


        # ---------------------------------------------
        # Get schools
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
        # No schools found
        # ---------------------------------------------

        if not schools:

            llm_response = (
                "I couldn't find any schools matching "
                "your request."
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
                school_id=None,
                school_name=None,
                sources=[]
            )


        # ---------------------------------------------
        # Build SQL response
        # ---------------------------------------------

        response_lines = []

        if detected_city:

            response_lines.append(
                f"Schools in {detected_city}:"
            )

        else:

            response_lines.append(
                "Available schools:"
            )


        for index, school_item in enumerate(
            schools,
            start=1
        ):

            location = ""

            if school_item.city:

                location = (
                    f" - {school_item.city}"
                )

            response_lines.append(
                f"{index}. "
                f"{school_item.name}"
                f"{location}"
            )


        llm_response = "\n".join(
            response_lines
        )


        print("\n" + "=" * 80)
        print("SQL RESULT")
        print("=" * 80)

        print(llm_response)


        _save_conversation(
            request.session_id,
            request.question,
            llm_response
        )


        return ChatResponse(
            question=request.question,
            rag_results=[],
            llm_response=llm_response,
            school_id=None,
            school_name=None,
            sources=[]
        )


    # =====================================================
    # 6. SQL + RAG ROUTE
    # =====================================================

    if intent == Intent.SQL_AND_RAG:

        print("\n" + "=" * 80)
        print("SQL + RAG ROUTE")
        print("=" * 80)

        # ---------------------------------------------
        # Find city
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

            if city and city.lower() in question_lower:

                detected_city = city

                break


        # ---------------------------------------------
        # SQL part
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


        sql_context_parts = []

        for school_item in schools:

            sql_context_parts.append(
                f"School: {school_item.name}\n"
                f"City: {school_item.city or 'Not available'}\n"
                f"State: {school_item.state or 'Not available'}\n"
                f"Address: {school_item.address or 'Not available'}\n"
                f"Phone: {school_item.phone or 'Not available'}\n"
                f"Email: {school_item.email or 'Not available'}"
            )


        sql_context = "\n\n".join(
            sql_context_parts
        )


        # ---------------------------------------------
        # Rewrite query
        # ---------------------------------------------

        if conversation_context:

            rewrite_input = f"""
Previous conversation:

{conversation_context}

Current user question:

{request.question}
"""

        else:

            rewrite_input = request.question


        rewritten_query = rewrite_query(
            rewrite_input
        )


        print("\nRewritten Query:")
        print(rewritten_query)


        # ---------------------------------------------
        # Generate embedding
        # ---------------------------------------------

        query_embedding = generate_embedding(
            rewritten_query
        )


        # ---------------------------------------------
        # Hybrid RAG search
        # ---------------------------------------------

        hybrid_results = hybrid_search(
            db=db,
            query=rewritten_query,
            query_embedding=query_embedding,
            school_id=school_id,
            top_k=10
        )


        # ---------------------------------------------
        # Reranking
        # ---------------------------------------------

        reranked_results = rerank_chunks(
            query=rewritten_query,
            chunks=hybrid_results,
            top_k=5
        )


        # ---------------------------------------------
        # Build RAG context
        # ---------------------------------------------

        rag_context = build_context(
            chunks=reranked_results,
            max_chunks=5
        )


        # ---------------------------------------------
        # Combine SQL + RAG context
        # ---------------------------------------------

        combined_context = f"""
================ SQL SCHOOL DATA ================

{sql_context}

================ SCHOOL PDF CONTEXT ================

{rag_context}

================ END CONTEXT ================
"""


        # ---------------------------------------------
        # Generate final answer
        # ---------------------------------------------

        llm_response = generate_answer(
            question=request.question,
            context=combined_context
        )


        # ---------------------------------------------
        # Build RAG results
        # ---------------------------------------------

        rag_results = _build_rag_results(
            db=db,
            chunks=reranked_results
        )


        sources = _build_sources(
            reranked_results
        )


        # ---------------------------------------------
        # Save conversation
        # ---------------------------------------------

        _save_conversation(
            request.session_id,
            request.question,
            llm_response
        )


        return ChatResponse(
            question=request.question,
            rag_results=rag_results,
            llm_response=llm_response,
            school_id=school_id,
            school_name=school_name,
            sources=sources
        )


    # =====================================================
    # 7. RAG ROUTE
    # =====================================================

    # RAG is also used for GENERAL questions because
    # the assistant should search school documents
    # whenever the question may be answered from PDFs.

    print("\n" + "=" * 80)
    print("RAG ROUTE")
    print("=" * 80)


    # =====================================================
    # 8. QUERY REWRITING
    # =====================================================

    if conversation_context:

        rewrite_input = f"""
Previous conversation:

{conversation_context}

Current user question:

{request.question}
"""

    else:

        rewrite_input = request.question


    rewritten_query = rewrite_query(
        rewrite_input
    )


    print("\n" + "=" * 80)
    print("REWRITTEN QUERY")
    print("=" * 80)

    print(rewritten_query)


    # =====================================================
    # 9. GENERATE QUERY EMBEDDING
    # =====================================================

    query_embedding = generate_embedding(
        rewritten_query
    )


    # =====================================================
    # 10. HYBRID SEARCH
    # =====================================================

    hybrid_results = hybrid_search(
        db=db,
        query=rewritten_query,
        query_embedding=query_embedding,
        school_id=school_id,
        top_k=10
    )


    # =====================================================
    # 11. NO RAG RESULTS
    # =====================================================

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


    # =====================================================
    # 12. RERANK
    # =====================================================

    reranked_results = rerank_chunks(
        query=rewritten_query,
        chunks=hybrid_results,
        top_k=5
    )


    # =====================================================
    # 13. BUILD CONTEXT
    # =====================================================

    context = build_context(
        chunks=reranked_results,
        max_chunks=5
    )


    print("\n" + "=" * 80)
    print("RERANKED RESULTS")
    print("=" * 80)


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


    # =====================================================
    # 14. FINAL CONTEXT
    # =====================================================

    print("\n" + "=" * 80)
    print("FINAL CONTEXT")
    print("=" * 80)

    print(context)


    # =====================================================
    # 15. GENERATE LLM ANSWER
    # =====================================================

    llm_response = generate_answer(
        question=request.question,
        context=context
    )


    # =====================================================
    # 16. BUILD RAG RESULTS
    # =====================================================

    rag_results = _build_rag_results(
        db=db,
        chunks=reranked_results
    )


    # =====================================================
    # 17. BUILD SOURCES
    # =====================================================

    sources = _build_sources(
        reranked_results
    )


    # =====================================================
    # 18. SAVE CONVERSATION MEMORY
    # =====================================================

    _save_conversation(
        request.session_id,
        request.question,
        llm_response
    )


    # =====================================================
    # 19. FINAL RESPONSE
    # =====================================================

    return ChatResponse(
        question=request.question,
        rag_results=rag_results,
        llm_response=llm_response,
        school_id=school_id,
        school_name=school_name,
        sources=sources
    )


# =========================================================
# HELPER: BUILD RAG RESULTS
# =========================================================

def _build_rag_results(
    db: Session,
    chunks: list[dict]
) -> list[RAGResult]:

    rag_results = []

    for chunk in chunks:

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

                page_number=chunk.get(
                    "page_number"
                ),

                content=chunk["content"],

                vector_score=chunk.get(
                    "vector_score"
                ),

                keyword_score=chunk.get(
                    "keyword_score"
                ),

                hybrid_score=chunk.get(
                    "hybrid_score"
                ),

                rerank_score=chunk.get(
                    "rerank_score"
                )
            )
        )

    return rag_results


# =========================================================
# HELPER: BUILD SOURCES
# =========================================================

def _build_sources(
    chunks: list[dict]
) -> list[ChatSource]:

    return [
        ChatSource(
            document_id=chunk["document_id"],

            page_number=chunk.get(
                "page_number"
            ),

            school_id=chunk["school_id"],

            rerank_score=chunk.get(
                "rerank_score"
            )
        )

        for chunk in chunks
    ]


# =========================================================
# HELPER: SAVE CONVERSATION
# =========================================================

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

    # Keep only latest 10 messages

    conversation_memory[
        session_id
    ] = conversation_memory[
        session_id
    ][-10:]