from qdrant_client import QdrantClient

def get_unique_categories_from_qdrant():
    try:
        client = QdrantClient(url="http://qdrant:6333") 
        categories = set()
        next_offset = None
        while True:
            response = client.scroll(
                collection_name="ucu_documents_e5_large",
                limit=100,
                with_payload=True,
                with_vectors=False,
                offset=next_offset
            )
            points, next_offset = response
            for point in points:
                cat = point.payload.get("access")
                if cat:
                    categories.add(cat)
            if next_offset is None:
                break
        return sorted(list(categories)) if categories else ["Public"]
    except Exception as e:
        print(f"Помилка Qdrant: {e}")
