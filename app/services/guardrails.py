"""
Guardrail fucntions using LLM:
- is_out_of_scope - checks if query is out of scope of UCU documents saved in Qdrant
- is_toxic - checks if input or output text is harmful
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=120.0
)
GEMINI_ANSWER_MODEL = "google/gemini-3-flash-preview"

def is_out_of_scope(query: str):
    """
    Checks if query is out of scope of UCU documents saved in Qdrant.
    """
    response = llm_client.chat.completions.create(
        model=GEMINI_ANSWER_MODEL,
        messages=[
            {
                "role": "system",
                "content": """Визнач чи питання стосується університету, навчання, 
                адміністративних процесів, документів або роботи УКУ.
                Відповідай ТІЛЬКИ: yes або no"""
            },
            {"role": "user", "content": query}
        ],
        temperature=0,
        max_tokens=5
    )
    answer = response.choices[0].message.content.strip().lower()
    return answer == "no"

def is_toxic(text: str):
    """
    Checks if text is harmful or dangerous.
    """
    response = llm_client.chat.completions.create(
        model=GEMINI_ANSWER_MODEL,
        messages=[
            {
                "role": "system",
                "content": """Визнач чи текст містить токсичний, образливий або 
                небезпечний контент. Відповідай ТІЛЬКИ: yes або no"""
            },
            {"role": "user", "content": text}
        ],
        temperature=0,
        max_tokens=5
    )
    answer = response.choices[0].message.content.strip().lower()
    return answer == "yes"
