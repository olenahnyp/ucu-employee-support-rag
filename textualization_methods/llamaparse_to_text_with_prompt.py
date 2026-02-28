"""
This file uses LlamaParse with a prompt to texualize pictures.
"""
import os
import nest_asyncio
from dotenv import load_dotenv
from llama_parse import LlamaParse

load_dotenv()

nest_asyncio.apply()

LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")
INPUT_FOLDER = "benchmark_dataset"
OUTPUT_FOLDER = 'benchmark_dataset_llamaparse_with_prompt'

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

INSTRUCTION = """Перед тобою сторінка зі звіту університету.\
    Напиши весь текст, який ти бачиш на сторінці.\
    1. Якщо бачиш графіки — опиши їх словами або таблицею.\
    2. Якщо бачиш карту України - випиши цифри та назви областей.\
    3. Якщо немає ні графіків, ні карти України - не згадуй їх.
"""

parser = LlamaParse(
    api_key=LLAMA_CLOUD_API_KEY,
    result_type="markdown",
    verbose=True,
    premium_mode=True,
    language="uk",
    parsing_instruction=INSTRUCTION
)

for root, dirs, files in os.walk(INPUT_FOLDER):
    for file in files:
        full_path = os.path.join(root, file)
        relative_path = os.path.relpath(root, INPUT_FOLDER)
        target_dir = os.path.join(OUTPUT_FOLDER, relative_path)
        os.makedirs(target_dir, exist_ok=True)
        file_name_only = os.path.splitext(file)[0]
        output_path = os.path.join(target_dir, f"{file_name_only}.md")
        try:
            documents = parser.load_data(full_path)
            full_text = "\n\n".join([doc.text for doc in documents])
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            print(f"File was textialized: {output_path}")
        except Exception as e:
            print(f"ERROR OCCURED: {str(e)}")
