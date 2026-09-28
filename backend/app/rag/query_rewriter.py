from langchain_openai import ChatOpenAI

from app.core.config import settings


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)


SYSTEM_PROMPT = """
You are a query rewriting component for a School AI Assistant.

Rewrite the user's question into a clear, standalone search query.

Rules:
1. Keep the original meaning.
2. Do not answer the question.
3. Do not add information that is not present.
4. Remove unnecessary conversational words.
5. Return only the rewritten query.
"""


def rewrite_query(question: str) -> str:
    prompt = f"""
{SYSTEM_PROMPT}

User Question:
{question}

Rewritten Search Query:
"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        raise RuntimeError(
            f"Failed to rewrite query: {str(e)}"
        )