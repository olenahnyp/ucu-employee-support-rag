from qdrant_client import QdrantClient

def get_unique_categories_from_qdrant():
    try:
        client = QdrantClient(url="http://qdrant:6333") 
        
        response = client.scroll(
            collection_name="ucu_documents_e5_large",
            with_payload=True,
            with_vectors=False
        )
        
        categories = set()
        for point in response[0]:
            cat = point.payload.get("category")
            if cat:
                categories.add(cat)
        
        return sorted(list(categories)) if categories else ["Public"]
    except Exception as e:
        print(f"Помилка Qdrant: {e}")
