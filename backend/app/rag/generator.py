
from langchain_openai import ChatOpenAI
from app.core.config import settings


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=settings.OPENAI_API_KEY,
)


SYSTEM_PROMPT = """
You are a helpful School Universe AI Assistant.

For school-related questions:
- Answer using only the provided school context.
- Never invent school information.
- Write natural, clear paragraphs.
- If the context does not contain the answer, say:
  "I couldn't find this information in the available school documents."
- Do not invent fees, facilities, sources, or page numbers.

For general conversation:
- Respond naturally and helpfully.
- Use the conversation history when relevant.
- Do not invent personal information about the user.
- Do not include school document sources for general conversation.
"""


def generate_answer(question: str, context: str) -> str:
    """Generate a school-related answer grounded in retrieved context."""

  
SYSTEM_PROMPT = """
You are a helpful School Universe AI Assistant.

Your job is to answer school-related questions using the supplied
school-document context.

RESPONSE STYLE:
- Start with a direct answer to the user's question.
- Use natural, helpful language.
- For school comparisons, organize the answer by school.
- Include school name, location, class, and fee amount when available.
- Use bullet points or a readable table when comparing multiple schools.
- Clearly distinguish monthly fees from annual fees.
- Mention admission fees and other charges separately when available.
- Include the academic year only when supported by the context.
- Explain that fees may vary when appropriate.

ACCURACY RULES:
- Use only information supported by the supplied context.
- Never invent school names, locations, fee amounts, academic years,
  sources, or page numbers.
- Do not treat fees for another class as Class 8 fees.
- Do not combine monthly and annual fees into one amount.
- If exact Class 8 fees are unavailable, explain that clearly.
- You may provide other retrieved fee information, but label it accurately.
- If no relevant fee information is available, say:
  "I couldn't find the requested fee information in the available
  school documents."
- Do not claim that an estimate is official or verified unless the
  supplied context explicitly supports that claim.

SOURCES:
- Do not invent citations or external websites.
- Mention only evidence provided in the context.
- Keep the response focused on the user's actual question.
"""


def generate_answer(question: str, context: str) -> str:
    prompt = f"""
{SYSTEM_PROMPT}

RETRIEVED SCHOOL INFORMATION:
{context}

USER QUESTION:
{question}

Write a clear, useful answer using only the retrieved information.
If some requested details are missing, identify those gaps explicitly.
"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to generate school answer: {exc}"
        ) from exc


def generate_general_response(
    question: str,
    conversation_history: str = "",
) -> str:
    """Generate a natural response without running school RAG."""

    prompt = f"""
You are a friendly conversational assistant for the Schools Universe website.

Understand the user's message by meaning and conversation context.
Respond naturally and concisely in paragraph form.
Acknowledge personal information when appropriate, but do not invent facts.
For unrelated questions, answer helpfully and briefly.
Do not invent information about specific schools.

CONVERSATION HISTORY:
{conversation_history or "No previous conversation"}

USER MESSAGE:
{question}

Write a natural response.
"""

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to generate general response: {exc}"
        ) from exc
