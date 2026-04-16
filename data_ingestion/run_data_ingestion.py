from connect_to_google_drive import sync_files
from connect_to_qdrant_db import sync_vectors_with_sheets
from gemini_textualization import run_textualization_pipeline

if __name__ == "__main__":
    sync_files()
    sync_vectors_with_sheets()
    run_textualization_pipeline()
