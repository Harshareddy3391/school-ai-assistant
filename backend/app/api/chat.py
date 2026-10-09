
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.school import SchoolKnowledge

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    RAGResult,
    SchoolInfo,
)

from app.services.embedding_service import generate_embedding
from app.services.school_service import resolve_school
from app.services.school_list_service import get_schools_by_city
from app.services.intent_router import detect_intent, Intent

from app.rag.query_rewriter import rewrite_query
from app.rag.hybrid_search import hybrid_search
from app.rag.reranker import rerank_chunks
from app.rag.context_builder import build_context
from app.rag.generator import (
    generate_answer,
    generate_general_response,
)

router = APIRouter(prefix="/chat", tags=["Chat"])

# Temporary in-memory conversation history
conversation_memory: dict[str, list[dict[str, str]]] = {}


def _save_conversation(
    session_id: str,
    question: str,
    answer: str,
) -> None:
    history = conversation_memory.setdefault(session_id, [])

    history.extend([
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer},
    ])

    conversation_memory[session_id] = history[-10:]


def _get_conversation_context(
    history: list[dict[str, str]],
) -> str:
    return "\n".join(
        f"{message['role'].upper()}: {message['content']}"
        for message in history
    )


def _school_info(row) -> SchoolInfo:
    return SchoolInfo(
        id=row["id"],
        name=row["name"],
        address=row.get("address"),
        city=row.get("city"),
        state=row.get("state"),
        phone=row.get("phone"),
        email=row.get("email"),
        website=row.get("website"),
    )


def _all_schools(db: Session) -> list[dict]:
    rows = (
        db.query(
            SchoolKnowledge.school_id,
            SchoolKnowledge.school_name,
            SchoolKnowledge.address,
            SchoolKnowledge.city,
            SchoolKnowledge.state,
            SchoolKnowledge.phone,
            SchoolKnowledge.email,
            SchoolKnowledge.website,
        )
        .distinct()
        .order_by(SchoolKnowledge.school_name)
        .all()
    )

    return [
        {
            "id": row.school_id,
            "name": row.school_name,
            "address": row.address,
            "city": row.city,
            "state": row.state,
            "phone": row.phone,
            "email": row.email,
            "website": row.website,
        }
        for row in rows
    ]


def _detect_city(db: Session, question: str) -> str | None:
    cities = (
        db.query(SchoolKnowledge.city)
        .filter(SchoolKnowledge.city.isnot(None))
        .distinct()
        .all()
    )

    question_lower = question.lower()

    for (city,) in cities:
        if city and city.lower() in question_lower:
            return city

    aliases = {
        "bangalore": "bengaluru",
        "bengaluru": "bangalore",
    }

    for requested, canonical in aliases.items():
        if requested in question_lower:
            for (city,) in cities:
                if city and canonical in city.lower():
                    return city

    return None


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    question = request.question.strip()
    session_id = request.session_id

    if not question:
        return ChatResponse(
            question=request.question,
            response_type="general",
            llm_response="Please enter a question.",
        )

    history = conversation_memory.get(session_id, [])
    conversation_context = _get_conversation_context(history)

    # 1. Fast-path common greetings.
    greetings = {
        "hi", "hii", "hiii", "hello", "hey",
        "good morning", "good afternoon",
        "good evening", "good night",
    }

    if question.lower().strip(" !.,?") in greetings:
        answer = (
            "Hi! How can I help you today? "
            "I can help you find schools or answer school-related questions."
        )

        _save_conversation(session_id, question, answer)

        return ChatResponse(
            question=question,
            response_type="general",
            llm_response=answer,
        )

    # 2. AI classifies the message using its meaning and conversation history.
    intent = detect_intent(
        question=question,
        conversation_history=conversation_context,
    )

    # 3. General conversation: do not run SQL school search or RAG.
    if intent == Intent.GENERAL:
        answer = generate_general_response(
            question=question,
            conversation_history=conversation_context,
        )

        _save_conversation(session_id, question, answer)

        return ChatResponse(
            question=question,
            response_type="general",
            llm_response=answer,
        )

    # 4. School search: use SQL only.
    if intent == Intent.SCHOOL_SEARCH:
        city = _detect_city(db, question)

        rows = (
            get_schools_by_city(db, city)
            if city
            else _all_schools(db)
        )

        schools = [_school_info(row) for row in rows]

        if schools:
            location_text = f" in {city}" if city else ""
            answer = (
                f"I found {len(schools)} school(s){location_text}. "
                "Here are the available schools."
            )
        else:
            answer = (
                f"I couldn't find schools"
                f"{f' in {city}' if city else ''} "
                "in the available school data."
            )

        _save_conversation(session_id, question, answer)

        return ChatResponse(
            question=question,
            response_type="school_list",
            llm_response=answer,
            schools=schools,
        )

    # 5. Rewrite the question so follow-ups retain context.
    rewrite_input = (
        f"Previous conversation:\n{conversation_context}\n\n"
        f"Current user question:\n{question}"
        if conversation_context
        else question
    )

    rewritten_query = rewrite_query(rewrite_input)

    # Resolve the school from either the current question or its
    # rewritten version, which may include context from previous turns.
    school = resolve_school(db=db, question=question)

    if school is None and rewritten_query != question:
        school = resolve_school(db=db, question=rewritten_query)

    selected_school_id = school.school_id if school else None
    selected_school_name = school.school_name if school else None

    # 6. SQL + RAG: search schools first, then retrieve their PDF chunks.
    if intent == Intent.SCHOOL_SEARCH_AND_KNOWLEDGE:
        city = _detect_city(db, question)

        sql_schools = (
            get_schools_by_city(db, city)
            if city
            else _all_schools(db)
        )

        sql_school_ids = list({
            row["id"] for row in sql_schools
        })

        if not sql_school_ids:
            answer = "I couldn't find matching schools in the available data."

            _save_conversation(session_id, question, answer)

            return ChatResponse(
                question=question,
                response_type="sql_and_rag",
                llm_response=answer,
            )

        query_embedding = generate_embedding(rewritten_query)

        hybrid_results = hybrid_search(
            db=db,
            query=rewritten_query,
            query_embedding=query_embedding,
            school_ids=sql_school_ids,
            top_k=10,
        )

    else:
        # 7. School knowledge: use RAG.
        query_embedding = generate_embedding(rewritten_query)

        hybrid_results = hybrid_search(
            db=db,
            query=rewritten_query,
            query_embedding=query_embedding,
            school_id=selected_school_id,
            top_k=10,
        )

    # 8. Handle missing document matches.
    if not hybrid_results:
        answer = (
            "I couldn't find this information in the "
            "available school documents."
        )

        _save_conversation(session_id, question, answer)

        return ChatResponse(
            question=question,
            response_type=(
                "sql_and_rag"
                if intent == Intent.SCHOOL_SEARCH_AND_KNOWLEDGE
                else "rag_answer"
            ),
            llm_response=answer,
            school_id=selected_school_id,
            school_name=selected_school_name,
        )

    # 9. Rerank the retrieved chunks and construct context.
    reranked_results = rerank_chunks(
        query=rewritten_query,
        chunks=hybrid_results,
        top_k=5,
    )

    context = build_context(
        chunks=reranked_results,
        max_chunks=5,
    )

    # 10. Generate an answer grounded in the school documents.
    answer = generate_answer(
        question=question,
        context=context,
    )

    # 11. Return relevant document chunks and source references.
    rag_results = [
        RAGResult(
            school_id=chunk["school_id"],
            school_name=chunk.get("school_name"),
            document_id=chunk.get("document_id") or 0,
            page_number=chunk.get("page_number"),
            content=chunk["content"],
            vector_score=chunk.get("vector_score"),
            keyword_score=chunk.get("keyword_score"),
            hybrid_score=chunk.get("hybrid_score"),
            rerank_score=chunk.get("rerank_score"),
        )
        for chunk in reranked_results
    ]

    sources = [
        ChatSource(
            document_id=chunk.get("document_id") or 0,
            page_number=chunk.get("page_number"),
            school_id=chunk["school_id"],
            rerank_score=chunk.get("rerank_score"),
        )
        for chunk in reranked_results
    ]

    _save_conversation(session_id, question, answer)

    return ChatResponse(
        question=question,
        response_type=(
            "sql_and_rag"
            if intent == Intent.SCHOOL_SEARCH_AND_KNOWLEDGE
            else "rag_answer"
        ),
        llm_response=answer,
        rag_results=rag_results,
        school_id=selected_school_id,
        school_name=selected_school_name,
        sources=sources,
    )
