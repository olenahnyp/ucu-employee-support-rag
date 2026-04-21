"""
This files run the whole textualization pipeline step by step:
1. Files sync with Google Drive and updating status in Google Sheets.
2. Textualize all the new files and save in PostreSQL.
3. Create vectors from texts and upload them into Qdrant.
"""

from connect_to_google_drive import sync_files
from connect_to_qdrant_db import sync_vectors_with_sheets
from gemini_textualization import run_textualization_pipeline

if __name__ == "__main__":
    sync_files()
    run_textualization_pipeline()
    sync_vectors_with_sheets()
