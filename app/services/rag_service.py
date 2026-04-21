"""
In this file data is retrieved from Qdrant based on user query and then passes into LLM
to generate final answer.
"""

import os
from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient, models
from qdrant_client.models import SparseTextEmbedding
from openai import OpenAI
from dotenv import load_dotenv
from app.services.guardrails import is_out_of_scope, is_toxic
from fastembed import SparseTextEmbedding

load_dotenv()

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = 6333
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

MODEL = SentenceTransformer('intfloat/multilingual-e5-large')
MODEL_SPARSE = SparseTextEmbedding(model_name="Qdrant/bm25")
COLLECTION_NAME = "ucu_documents_e5_large"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LLM_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    timeout=120.0
)
GEMINI_ANSWER_MODEL = "google/gemini-3-flash-preview"

RERANKER = CrossEncoder("BAAI/bge-reranker-v2-m3")

def transform_query(query):
    prompt = f"""
    Ти — експерт з документообігу та адміністративних процесів Українського Католицького Університету (УКУ).

    Твоє завдання — переформулювати запит користувача у чітке, формальне та структуроване питання, оптимізоване для пошуку в інституційній базі знань.

    Вимоги:
    - Збережи початковий зміст запиту без змін.
    - Не додавай нової інформації та не вигадуй фактів.
    - Сфокусуйся на ключових термінах, які можуть використовуватися в офіційних документах (наприклад: політика, регламент, процедура, наказ, положення).
    - Замінюй розмовні формулювання на формальні.
    - Якщо запит уже є чітким і формальним — залиш його без змін.

    Формат відповіді:
    - Одне переформульоване питання.
    - Без пояснень, без додаткового тексту.

    Запит користувача: {query}
    """
    response = LLM_CLIENT.chat.completions.create(
        model=GEMINI_ANSWER_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1
    )
    return response.choices[0].message.content

def search_with_reranker(query: str, allowed_categories=None, initial_k: int = 10, final_k: int = 3):
    """
    Here chunks are retrieved from Qdrant and then reranked.
    """
    print(f"Запит: '{query}'")
    
    original_query_text = query
    query_formal = transform_query(original_query_text) 
    query_vector = MODEL.encode("query: " + query_formal)

    query_filter = models.Filter(
        must_not=[models.HasIdCondition(has_id=[])]
    )
    print(allowed_categories)
    if allowed_categories:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="access",
                    match=models.MatchAny(any=allowed_categories)
                )
            ]
        )
    else:
        return "У вас немає доступу до жодних документів."

    search_results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        using="default",
        query_filter=query_filter,
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
    Ти — інтелектуальний асистент для працівників Українського Католицького Університету (УКУ). Твоя мета — надавати точні, лаконічні та професійні відповіді на основі внутрішньої документації університету.

    Джерело знань:
    - Твої відповіді мають базуватися ВИКЛЮЧНО на наданому контексті.
    - Якщо контекст не містить достатньо інформації, ти ПОВИНЕН відповісти: "На жаль, у наданих документах немає достатньо інформації для точної відповіді на це запитання."
    - ЗАБОРОНЕНО використовувати зовнішні знання або вигадувати факти (hallucinations).

    Правила обробки та безпеки:
    1. Персональні дані: Якщо в тебе запитують щось про конкретних людей, то не згадуй їх імена, а тільки ініціали та прізвище.
    2. Актуальність: При запиті статистичних або регуляторних даних без вказівки року, пріоритезуй документи з найпізнішою датою у назві або метаданих.
    3. Мова та стиль: Використовуй офіційно-діловий стиль української мови. Відповідь має бути чіткою та структурованою (використовуй списки, якщо це доречно).

    Форматування та посилання:
    - Після кожної тези або в кінці відповіді обов'язково вказуй джерело у форматі: [Джерело: Назва_файлу].
    - Якщо відповідь базується на кількох документах, перелічи їх через кому.
    - Виділяй ключові терміни або суми **жирним шрифтом** для кращої читабельності.
    """
    user_message = f"КОНТЕКСТ З БАЗИ ДАНИХ:\n{retrieved_context}\n\nЗАПИТАННЯ КОРИСТУВАЧА:\n{query}"

    response = LLM_CLIENT.chat.completions.create(
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

def run_rag_pipeline(query, allowed_categories):
    result = search_with_reranker(query, allowed_categories)
    answer = generate_answer_with_guardrails(query, result)
    return f"{answer['answer']}"

# if __name__ == "__main__":
#     query = input("Введіть ваше запитання: ")
#     result = search_with_reranker(query)
#     answer = generate_answer_with_guardrails(query, result)
#     print(answer["answer"])