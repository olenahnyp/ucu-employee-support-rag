"""
In this file data is retrieved from Qdrant based on user query and then passes into LLM
to generate final answer.
"""

import os
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient, models
from openai import OpenAI
from dotenv import load_dotenv
from guardrails import is_out_of_scope, is_toxic

load_dotenv()

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

MODEL = SentenceTransformer('intfloat/multilingual-e5-base')
COLLECTION_NAME = "ucu_documents_e5_base"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=120.0
)
GEMINI_ANSWER_MODEL = "google/gemini-3-flash-preview"

RERANKER = CrossEncoder("BAAI/bge-reranker-v2-m3")

def search_with_reranker(query: str, initial_k: int = 10, final_k: int = 3):
    """
    Here chunks are retrieved from Qdrant and then reranked.
    """
    print(f"Запит: '{query}'")
    
    original_query_text = query 
    
    query_vector = MODEL.encode("query: " + query)

    search_results = client.query_points(
        collection_name=COLLECTION_NAME,
        prefetch=[
            models.Prefetch(
                query=query_vector,
                using="default",
                limit=initial_k
            )
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=initial_k
    )

    if not search_results or not search_results.points:
        return "На жаль, за цим запитом нічого не знайдено."

    documents = []
    for hit in search_results.points:
        text = hit.payload.get("text", "")
        source = hit.payload.get("file_name", "Невідомий документ")
        documents.append({"text": text, "source": source})

    cross_input = [[original_query_text, doc["text"]] for doc in documents]
    
    rerank_scores = RERANKER.predict(cross_input)

    for i in range(len(documents)):
        documents[i]["cross_score"] = float(rerank_scores[i])

    documents = sorted(documents, key=lambda x: x["cross_score"], reverse=True)

    context_blocks = []
    for doc in documents[:final_k]:
        block = f"[Джерело: {doc['source']} | Реранк: {doc['cross_score']:.2f}]\n{doc['text']}"
        context_blocks.append(block)

    return "\n\n---\n\n".join(context_blocks)

def generate_final_answer(query: str, retrieved_context: str):
    """
    This functions uses Gemini to generate final answer.
    """
    system_prompt = """
    Ти є інтелектуальним помічником для працівників Українського Католицького Університету (УКУ).
    Твоє завдання — відповісти на запитання користувача, спираючись ВИКЛЮЧНО на наданий контекст з внутрішніх документів.

    ПРАВИЛА:
    1. Якщо в контексті немає відповіді, чесно скажи: "На жаль, у знайдених документах немає інформації для відповіді на це запитання." Не вигадуй жодних фактів.
    2. Формулюй відповідь чітко, професійно та структуровано.
    3. Якщо в тебе запитують щось про конкретних людей, то не згадуй їх імена, якщо імен немає джерелі, а тільки ініціали та прізвище.
    4. Якщо питають якісь статистичні дані і не вказують рік, то бери найактуальніші документи.
    5. Обов'язково вказуй джерело інформації у форматі: [Джерело: Назва_файлу.pdf].
    """

    user_message = f"КОНТЕКСТ З БАЗИ ДАНИХ:\n{retrieved_context}\n\nЗАПИТАННЯ КОРИСТУВАЧА:\n{query}"

    response = llm_client.chat.completions.create(
        model=GEMINI_ANSWER_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
            max_tokens=1000,
            timeout=120.0
    )
    return response.choices[0].message.content

def generate_answer_with_guardrails(query: str, retrieved_context: str):
    """
    In this fucntion guardrails are used for input and output.
    """
    if is_out_of_scope(query):
        return {
            "answer": "Я можу відповідати лише на питання про УКУ — навчання, адміністративні процеси, документи тощо.",
            "guardrail_triggered": "scope"
        }

    if is_toxic(query):
        return {
            "answer": "Запит містить недопустимий контент. Будь ласка, переформулюй питання.",
            "guardrail_triggered": "toxic_input"
        }

    answer = generate_final_answer(query, retrieved_context)

    if is_toxic(answer):
        return {
            "answer": "Вибач, не можу надати таку відповідь.",
            "guardrail_triggered": "toxic_output"
        }

    return {
        "answer": answer,
        "guardrail_triggered": None
    }

if __name__ == "__main__":
    query = input("Введіть ваше запитання: ")
    result = search_with_reranker(query)
    answer = generate_answer_with_guardrails(query, result)
    print(answer["answer"])