from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    SQL = "sql"
    RAG = "rag"
    SQL_AND_RAG = "sql_and_rag"
    GENERAL = "general"


def detect_intent(question: str):
    q = question.lower().strip()

    # -------------------------
    # GREETING
    # -------------------------
    greeting_words = [
        "hi",
        "hii",
        "hiii",
        "hello",
        "hey",
        "heyy",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
    ]

    if q in greeting_words:
        return Intent.GREETING

    # -------------------------
    # SQL / SCHOOL LIST
    # -------------------------
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

    # -------------------------
    # RAG / PDF INFORMATION
    # -------------------------
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

    has_sql = any(keyword in q for keyword in sql_keywords)
    has_rag = any(keyword in q for keyword in rag_keywords)

    if has_sql and has_rag:
        return Intent.SQL_AND_RAG

    if has_sql:
        return Intent.SQL

    if has_rag:
        return Intent.RAG

    return Intent.GENERAL