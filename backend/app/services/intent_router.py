
from enum import Enum

from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from app.core.config import settings


class Intent(str, Enum):
    GENERAL = "general"
    SCHOOL_SEARCH = "school_search"
    SCHOOL_KNOWLEDGE = "school_knowledge"
    SCHOOL_SEARCH_AND_KNOWLEDGE = "school_search_and_knowledge"


class IntentDecision(BaseModel):
    intent: Intent = Field(
        description="The most appropriate intent for the user's message"
    )


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY,
)

intent_classifier = llm.with_structured_output(IntentDecision)


def detect_intent(
    question: str,
    conversation_history: str = "",
) -> Intent:
    prompt = f"""
Classify the user's latest message based on its meaning and conversation context.

Choose exactly one intent:

1. general:
   Normal conversation, greetings, personal statements, thanks,
   general questions, or topics unrelated to finding schools or
   information in school documents.

2. school_search:
   The user wants to find, list, filter, or locate schools.
   Examples: schools in Chennai, schools near Bangalore,
   list schools in Hyderabad.

3. school_knowledge:
   The user asks for specific information from school documents.
   Examples: admission process, fees, eligibility, facilities,
   required documents, school timings, or transport.

4. school_search_and_knowledge:
   The user wants to find schools AND compare or retrieve
   information about those schools.
   Examples: find schools in Chennai and compare their fees.

Use the conversation history to interpret follow-up questions.
For example, "What about its fees?" may refer to a school
discussed earlier and should be classified as school_knowledge.

Do not classify a message as school-related merely because it
contains a common word that appeared in an earlier school question.
Classify based on the user's actual meaning.

Conversation history:
{conversation_history or "No previous conversation"}

Latest user message:
{question}
"""

    result = intent_classifier.invoke(prompt)
    return result.intent
