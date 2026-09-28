from langchain_openai import ChatOpenAI

from app.core.config import settings


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY
)


SYSTEM_PROMPT = """
You are a School AI Assistant.

Your job is to answer the user's question using ONLY the information
provided in the school context.

Rules:

1. Use only information available in the provided context.
2. Never invent, assume, or guess information.
3. If the requested information is not present in the context, say:
   "I couldn't find this information in the available school documents."
4. When information from multiple schools is available, clearly mention
   the relevant school names.
5. Keep the answer clear, direct, and easy to understand.
6. If the user asks for a comparison, compare only the information
   available in the context.
7. If the user asks for a calculation or comparison, use only the
   retrieved values from the context.
8. Do not treat missing information as zero, unknown values, or estimates.
9. Do not mention embeddings, vector search, hybrid search, reranking,
   retrieval, or other internal system processes.
10. Do not create sources or page numbers that are not present in the context.
11. If the context contains multiple relevant answers, summarize them
    clearly instead of returning only one result.
"""


def generate_answer(
    question: str,
    context: str
) -> str:

    prompt = f"""
{SYSTEM_PROMPT}

================ SCHOOL CONTEXT ================

{context}

================ END SCHOOL CONTEXT ================

USER QUESTION:
{question}

IMPORTANT:
Answer the user's question using only the school context above.

FINAL ANSWER:
"""

    try:
        response = llm.invoke(prompt)

        return response.content.strip()

    except Exception as e:
        raise RuntimeError(
            f"Failed to generate answer: {str(e)}"
        )