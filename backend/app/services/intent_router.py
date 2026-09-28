from enum import Enum


class Intent(str, Enum):
    SCHOOL_INFO = "school_info"
    SCHOOL_LIST = "school_list"
    GENERAL = "general"


def detect_intent(question: str) -> Intent:
    question_lower = question.lower()

    # School listing / location questions
    list_keywords = [
        "schools in",
        "schools near",
        "school in",
        "school near",
        "location schools",
        "schools located",
        "list schools",
        "show schools",
        "find schools",
    ]

    for keyword in list_keywords:
        if keyword in question_lower:
            return Intent.SCHOOL_LIST

    # Questions about a particular school
    school_keywords = [
        "admission",
        "fee",
        "fees",
        "phone",
        "contact",
        "email",
        "address",
        "location",
        "board",
        "classes",
        "facilities",
        "documents",
    ]

    for keyword in school_keywords:
        if keyword in question_lower:
            return Intent.SCHOOL_INFO

    return Intent.GENERAL