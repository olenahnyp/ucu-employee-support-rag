"""
This file is used for textualization of all files with status pending in Google Sheets.
"""
import io
import os
import base64
import fitz
import pandas as pd
import psycopg2
from openai import OpenAI
from PIL import Image
from dotenv import load_dotenv
from googleapiclient.http import MediaIoBaseDownload
from connect_to_google_drive import get_drive_service, get_sheets_client, SHEET_ID

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL_NAME = "google/gemini-3-flash-preview"

def save_to_postgres(file_id, file_name, content):
    """
    Save a document to PostgreSQL.
    """
    try:
        conn = psycopg2.connect(
            dbname="ucu_rag_db", user="user", password="password", host="127.0.0.1", port=5432
        )
        cur = conn.cursor()
        query = """
            INSERT INTO processed_documents (google_drive_id, file_name, markdown_content)
            VALUES (%s, %s, %s)
            ON CONFLICT (google_drive_id) 
            DO UPDATE SET markdown_content = EXCLUDED.markdown_content, 
                          processed_at = CURRENT_TIMESTAMP;
        """
        cur.execute(query, (file_id, file_name, content))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"ERROR: {e}")

def encode_pil_image(img):
    """
    Resizes an image and encodes it into a Base64 string.
    """
    if img.mode != 'RGB':
        img = img.convert('RGB')

    max_size = 1024
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')

def run_textualization_pipeline():
    """
    Textualizes all files with pending status and saves markdown files locally.
    """
    drive_service = get_drive_service()
    sheets_client = get_sheets_client()
    sheet = sheets_client.open_by_key(SHEET_ID).sheet1

    all_records = sheet.get_all_records()
    if not all_records:
        return

    df = pd.DataFrame(all_records)
    pending_files = df[df['status'] == 'Pending']

    if pending_files.empty:
        print("No new files")
        return

    zoom = 2
    prompt_text = "Перед тобою сторінка зі звіту університету.\
        Напиши весь текст, який ти бачиш на сторінці.\
        1. Якщо бачиш графіки — опиши їх словами або таблицею.\
        2. Якщо бачиш карту України - випиши цифри та назви областей.\
        3. Якщо немає ні графіків, ні карти України - не згадуй їх"

    for index, row in pending_files.iterrows():
        file_id = row['google_drive_id']
        file_name = row['file_name']
        print(f"Textualizing file {file_name}") 
        try:
            request = drive_service.files().get_media(fileId=file_id)
            file_stream = io.BytesIO()
            downloader = MediaIoBaseDownload(file_stream, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()      
            pdf_file = fitz.open(stream=file_stream.getvalue(), filetype="pdf")
            full_markdown = f"# {file_name}\n\n"

            for page_index, page in enumerate(pdf_file):
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)         
                img_from_pix = Image.open(io.BytesIO(pix.tobytes("png")))           
                base64_image = encode_pil_image(img_from_pix)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt_text},
                            {"type": "image_url", "image_url": 
                            {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }]
                )    
                result_text = response.choices[0].message.content
                full_markdown += f"## Сторінка {page_index + 1}\n\n{result_text}\n\n---\n\n"
            os.makedirs("output_texts", exist_ok=True)
            with open(f"output_texts/{os.path.splitext(file_name)[0]}.md", "w", encoding="utf-8") as f:
                f.write(full_markdown)        
            save_to_postgres(file_id, file_name, full_markdown)
            df.at[index, 'status'] = 'Success'
            print(f"File {file_name} textualized")

        except Exception as e:
            print(f"ERROR: {e}")
            df.at[index, 'status'] = 'Error'

    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())

if __name__ == "__main__":
    run_textualization_pipeline()
