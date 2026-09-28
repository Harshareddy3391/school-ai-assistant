from enum import Enum


class Intent(str, Enum):
    SQL = "sql"
    RAG = "rag"
    SQL_AND_RAG = "sql_and_rag"
    GENERAL = "general"


def detect_intent(question: str) -> Intent:

    question_lower = question.lower()

    # ==========================================
    # SQL QUESTIONS
    # ==========================================

    sql_keywords = [
        "schools in",
        "schools near",
        "school in",
        "school near",
        "schools located",
        "list schools",
        "show schools",
        "find schools",
        "how many schools",
        "which schools",
        "school names",
    ]

    # ==========================================
    # RAG QUESTIONS
    # ==========================================

    rag_keywords = [
        "admission",
        "fee",
        "fees",
        "documents",
        "facilities",
        "curriculum",
        "subjects",
        "activities",
        "transport",
        "hostel",
        "library",
        "laboratory",
        "sports",
        "timings",
        "rules",
        "eligibility",
        "procedure",
        "requirements",
        "about the school",
    ]

    has_sql = any(
        keyword in question_lower
        for keyword in sql_keywords
    )

    has_rag = any(
        keyword in question_lower
        for keyword in rag_keywords
    )

    # ==========================================
    # SQL + RAG
    # ==========================================

    if has_sql and has_rag:
        return Intent.SQL_AND_RAG

    # ==========================================
    # SQL ONLY
    # ==========================================

    if has_sql:
        return Intent.SQL

    # ==========================================
    # RAG ONLY
    # ==========================================

    if has_rag:
        return Intent.RAG

    # ==========================================
    # GENERAL
    # ==========================================

    return Intent.GENERAL