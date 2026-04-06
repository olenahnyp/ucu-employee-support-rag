import os
import json
import math
from sentence_transformers import CrossEncoder
from openai import OpenAI
from qdrant_client import QdrantClient, models
from thefuzz import fuzz
from fastembed import SparseTextEmbedding

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
CLIENT = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

MODEL_RERANKER = CrossEncoder('BAAI/bge-reranker-v2-m3')
MODEL_SPARSE = SparseTextEmbedding(model_name="Qdrant/bm25")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LLM_CLIENT = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

OPENROUTER_MODEL = "google/gemini-3-flash-preview"

with open("final_golden_dataset.json", "r", encoding="utf-8") as f:
    golden_data = json.load(f)

def is_similar(text1, text2, threshold=80):
    return fuzz.partial_ratio(text1.strip(), text2.strip()) >= threshold

def get_reranked_results(query, initial_results, k=5):
    points = initial_results.points
    pairs = [[query, res.payload['text']] for res in points]
    scores = MODEL_RERANKER.predict(pairs)
    scored_results = sorted(zip(points, scores), key=lambda x: x[1], reverse=True)

    return [res[0] for res in scored_results[:k]]

def evaluate_retrieval_metrics(search_results, golden_context, k=5):
    hit = 0
    reciprocal_rank = 0
    dcg = 0
    found_golden_indices = set()
    
    for rank, result in enumerate(search_results[:k], start=1):
        for i, golden_text in enumerate(golden_context):
            if i not in found_golden_indices:
                if is_similar(golden_text, result):
                    if hit == 0:
                        hit = 1
                        reciprocal_rank = 1 / rank
                    
                    found_golden_indices.add(i)
                    dcg += 1 / math.log2(rank + 1)
                    break

    relevant_found_count = len(found_golden_indices)
    recall = relevant_found_count / len(golden_context) if len(golden_context) > 0 else 0
    
    idcg = sum(1 / math.log2(i + 1) for i in range(1, min(len(golden_context), k) + 1))
    ndcg = dcg / idcg if idcg > 0 else 0
    
    return hit, reciprocal_rank, recall, ndcg

def get_metrics(model, collection, e5=False, openai_client=None):
    total_hit = 0
    total_mrr = 0
    total_recall = 0
    total_ndcg = 0

    total_hit_reranked = 0
    total_mrr_reranked = 0
    total_recall_reranked = 0
    total_ndcg_reranked = 0

    for item in golden_data:
        if openai_client:
            response = openai_client.embeddings.create(
                input=[item['input'].replace("\n", " ")],
                model="text-embedding-3-large"
            )
            query = response.data[0].embedding
        elif e5:
            query = model.encode("query: " + item['input']).tolist()
        else:
            query=model.encode(item['input']).tolist()
        results = CLIENT.query_points(
            collection_name=collection,
            prefetch=[
                models.Prefetch(
                    query=query,
                    using="default",
                    limit=20
                )
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=20
        )
        found_texts = [res.payload['text'] for res in results.points]
        
        h, m, r, n = evaluate_retrieval_metrics(found_texts, item['retrieval_context'])
        total_hit += h
        total_mrr += m
        total_recall += r
        total_ndcg += n

        reranked_objects = get_reranked_results(item['input'], results)
        reranked_texts = [res.payload['text'] for res in reranked_objects]

        h_rerank, m_rerank, r_rerank, n_rerank = evaluate_retrieval_metrics(reranked_texts, item['retrieval_context'])
        total_hit_reranked += h_rerank
        total_mrr_reranked += m_rerank
        total_recall_reranked += r_rerank
        total_ndcg_reranked += n_rerank

    return total_hit, total_mrr, total_recall, total_ndcg, \
            total_hit_reranked, total_mrr_reranked, total_recall_reranked, total_ndcg_reranked

def generate_hypothetical_answer(query, gemini_model):
    prompt = f"""
    Ти — асистент адміністрації Українського Католицького Університету (УКУ).
    Згенеруй короткий фрагмент тексту, який міг би бути частиною офіційного документа або політики УКУ та містити відповідь на запит користувача.
    Використовуй формальний стиль і термінологію, характерну для нормативних документів університету. Формулюй текст так, щоб він був схожий на реальні положення, інструкції або регламенти.
    Текст має бути лаконічним, але включати ключові терміни та варіанти формулювань, які можуть використовуватися в офіційних джерелах.

    Запитання: {query}
    """
    response = LLM_CLIENT.chat.completions.create(
        model=gemini_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1
    )
    return response.choices[0].message.content

def get_metrics_hyde(model, collection, e5=False, openai_client=None, sparse_model=None):
    total_hit = 0
    total_mrr = 0
    total_recall = 0
    total_ndcg = 0

    total_hit_reranked = 0
    total_mrr_reranked = 0
    total_recall_reranked = 0
    total_ndcg_reranked = 0

    for item in golden_data:
        hyde_doc = generate_hypothetical_answer(item['input'], OPENROUTER_MODEL)
        if openai_client:
            response = openai_client.embeddings.create(
                input=[item['input'].replace("\n", " ")],
                model="text-embedding-3-large"
            )
            query_vector = response.data[0].embedding
        elif e5:
            query_vector = model.encode("query: " + hyde_doc).tolist()
        else:
            query_vector = model.encode(hyde_doc).tolist()

        if sparse_model:
            results = CLIENT.query_points(
                collection_name=collection,
                prefetch=[
                    models.Prefetch(
                        query=query_vector,
                        using="default",
                        limit=20
                    )
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=20
            ) 
        else:
            results = CLIENT.query_points(
                collection_name=collection,
                prefetch=[
                    models.Prefetch(
                        query=query_vector,
                        using="default",
                        limit=20
                    )
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=20
            )
        found_texts = [res.payload['text'] for res in results.points]
        
        h, m, r, n = evaluate_retrieval_metrics(found_texts, item['retrieval_context'])
        total_hit += h
        total_mrr += m
        total_recall += r
        total_ndcg += n

        reranked_objects = get_reranked_results(item['input'], results)
        reranked_texts = [res.payload['text'] for res in reranked_objects]

        h_rerank, m_rerank, r_rerank, n_rerank = evaluate_retrieval_metrics(reranked_texts, item['retrieval_context'])
        total_hit_reranked += h_rerank
        total_mrr_reranked += m_rerank
        total_recall_reranked += r_rerank
        total_ndcg_reranked += n_rerank

    return total_hit, total_mrr, total_recall, total_ndcg, \
            total_hit_reranked, total_mrr_reranked, total_recall_reranked, total_ndcg_reranked

def transform_query(query, gemini_model):
    prompt = f"""
    Ти — експерт з документообігу та адміністративних процесів Українського Католицького Університету (УКУ). 
    Твоє завдання — переформулювати запит користувача у чітке, формальне та структуроване питання, придатне для пошуку в інституційній базі знань. 
    Збережи початковий зміст запиту, покращуючи його точність, зрозумілість і формальність.
    Відповідь має містити лише одне переформульоване питання у формальному стилі, без пояснень чи додаткового тексту.
    Запит користувача: {query}"""
    response = LLM_CLIENT.chat.completions.create(
        model=gemini_model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1
    )
    return response.choices[0].message.content

def get_metrics_query_transform(model, collection, e5=False, openai_client=None, sparse_model=None):
    total_hit = 0
    total_mrr = 0
    total_recall = 0
    total_ndcg = 0

    total_hit_reranked = 0
    total_mrr_reranked = 0
    total_recall_reranked = 0
    total_ndcg_reranked = 0

    for item in golden_data:
        query_formal = transform_query(item['input'], OPENROUTER_MODEL)
        if openai_client:
            response = openai_client.embeddings.create(
                input=[item['input'].replace("\n", " ")],
                model="text-embedding-3-large"
            )
            query_vector = response.data[0].embedding
        elif e5:
            query_vector = model.encode("query: " + query_formal).tolist()
        else:
            query_vector = model.encode(query_formal).tolist()

        if sparse_model:
            sparse_emb = list(sparse_model.embed([item['input']]))[0]
            results = CLIENT.query_points(
                collection_name=collection,
                prefetch=[
                    models.Prefetch(
                        query=query_vector,
                        using="default",
                        limit=20
                    ),
                    models.Prefetch(
                        query=models.SparseVector(
                        indices=sparse_emb.indices.tolist(),
                        values=sparse_emb.values.tolist()
                    ),
                        using="text_sparse",
                        limit=20
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=20
            )
        else:
            results = CLIENT.query_points(
                collection_name=collection,
                prefetch=[
                    models.Prefetch(
                        query=query_vector,
                        using="default",
                        limit=20
                    )
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=20
            )
        found_texts = [res.payload['text'] for res in results.points]
        
        h, m, r, n = evaluate_retrieval_metrics(found_texts, item['retrieval_context'])
        total_hit += h
        total_mrr += m
        total_recall += r
        total_ndcg += n

        reranked_objects = get_reranked_results(item['input'], results)
        reranked_texts = [res.payload['text'] for res in reranked_objects]

        h_rerank, m_rerank, r_rerank, n_rerank = evaluate_retrieval_metrics(reranked_texts, item['retrieval_context'])
        total_hit_reranked += h_rerank
        total_mrr_reranked += m_rerank
        total_recall_reranked += r_rerank
        total_ndcg_reranked += n_rerank

    return total_hit, total_mrr, total_recall, total_ndcg, \
            total_hit_reranked, total_mrr_reranked, total_recall_reranked, total_ndcg_reranked

def get_metrics_sparse(model, collection, sparse_model, e5=False, openai_client=None):
    total_hit = 0
    total_mrr = 0
    total_recall = 0
    total_ndcg = 0

    total_hit_reranked = 0
    total_mrr_reranked = 0
    total_recall_reranked = 0
    total_ndcg_reranked = 0

    for item in golden_data:
        if openai_client:
            response = openai_client.embeddings.create(
                input=[item['input'].replace("\n", " ")],
                model="text-embedding-3-large"
            )
            dense_vector = response.data[0].embedding
        elif e5:
            dense_vector = model.encode("query: " + item['input']).tolist()
        else:
            dense_vector = model.encode(item['input']).tolist()
        sparse_emb = list(sparse_model.embed([item['input']]))[0]
            
        results = CLIENT.query_points(
            collection_name=collection,
            prefetch=[
                models.Prefetch(
                    query=dense_vector,
                    using="default",
                    limit=20
                ),
                models.Prefetch(
                    query=models.SparseVector(
                    indices=sparse_emb.indices.tolist(),
                    values=sparse_emb.values.tolist()
                ),
                    using="text_sparse",
                    limit=20
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=20
        )
        found_texts = [res.payload['text'] for res in results.points]
        
        h, m, r, n = evaluate_retrieval_metrics(found_texts, item['retrieval_context'])
        total_hit += h
        total_mrr += m
        total_recall += r
        total_ndcg += n

        reranked_objects = get_reranked_results(item['input'], results)
        reranked_texts = [res.payload['text'] for res in reranked_objects]

        h_rerank, m_rerank, r_rerank, n_rerank = evaluate_retrieval_metrics(reranked_texts, item['retrieval_context'])
        total_hit_reranked += h_rerank
        total_mrr_reranked += m_rerank
        total_recall_reranked += r_rerank
        total_ndcg_reranked += n_rerank

    return total_hit, total_mrr, total_recall, total_ndcg, \
            total_hit_reranked, total_mrr_reranked, total_recall_reranked, total_ndcg_reranked
