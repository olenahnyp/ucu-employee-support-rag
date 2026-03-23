"""
In this file we retrieve texts from PostgreSQL and uload vectorized data into Qdrant.
"""
import uuid
import pandas as pd
import psycopg2
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from connect_to_google_drive import get_sheets_client, SHEET_ID

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
COLLECTION_NAME = "ucu_documents_e5_large"

model = SentenceTransformer('intfloat/multilingual-e5-large')

def get_text_from_postgres(file_id):
    """
    Get textualized file from PostreSQL by file ID.
    """
    try:
        conn = psycopg2.connect(
            dbname="ucu_rag_db", user="user", password="password", host="127.0.0.1"
        )
        cur = conn.cursor()
        cur.execute(
            "SELECT markdown_content FROM processed_documents WHERE google_drive_id = %s", 
            (file_id,)
        )
        result = cur.fetchone()
        cur.close()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def sync_vectors_with_sheets():
    """
    This function connects to Qdrant database and loads there all files with success status from Google Sheets.
    Additionally, it removes all the files with deleted status.
    """
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    sheets_client = get_sheets_client()
    sheet = sheets_client.open_by_key(SHEET_ID).sheet1
    df = pd.DataFrame(sheet.get_all_records())

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
        )

    deleted_files = df[df['status'] == 'Deleted']
    for _, row in deleted_files.iterrows():
        file_id = row['google_drive_id']
        
        client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[models.FieldCondition(key="file_id", match=models.MatchValue(value=file_id))]
                )
            )
        )

        df.loc[df['google_drive_id'] == file_id, 'vector_db_sync'] = 'Yes'

    to_sync = df[(df['status'] == 'Success') & (df['vector_db_sync'] == 'No')]
    
    for index, row in to_sync.iterrows():
        file_id = row['google_drive_id']
        file_name = row['file_name']
        
        text = get_text_from_postgres(file_id)

        if text:
            chunks = [text[i:i+1000] for i in range(0, len(text), 800)]
            
            print(f"File {file_name} in progress")
            
            for i, chunk in enumerate(chunks):
                vector = model.encode("passage: " + chunk).tolist()
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{file_id}_{i}"))
                client.upsert(
                    collection_name=COLLECTION_NAME,
                    points=[
                        models.PointStruct(
                            id=point_id,
                            vector=vector,
                            payload={
                                "file_id": file_id,
                                "file_name": file_name,
                                "text": chunk,
                                "chunk_index": i
                            }
                        )
                    ]
                )
            
            df.at[index, 'vector_db_sync'] = 'Yes'

    df = df[~((df['status'] == 'Deleted') & (df['vector_db_sync'] == 'Yes'))]
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

if __name__ == "__main__":
    sync_vectors_with_sheets()
