"""
This file uses Gemini model to textualize pictures.
"""
import os
import io
import base64
import time
import re
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL_NAME = "google/gemini-3-flash-preview"

IMAGE_FOLDER = "benchmark_dataset_snapshots"
OUTPUT_FOLDER = "benchmark_dataset_free_vision_model"

def natural_keys(text):
    """
    This function is used to sort pages.
    """
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', text)]

def encode_image(image_path):
    """
    Resizes an image and encodes it into a Base64 string.
    """
    with Image.open(image_path) as img:
        if img.mode != 'RGB':
            img = img.convert('RGB')

        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size))

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

for root, dirs, files in os.walk(IMAGE_FOLDER):
    current_folder_photos = sorted(
    [f for f in files if f.lower().endswith((".png", ".jpg", ".jpeg"))],
        key=natural_keys
    )

    if not current_folder_photos:
        continue

    folder_name = os.path.basename(root)
    print(f'Current folder: {folder_name}')

    relative_path_to_parent = os.path.relpath(os.path.dirname(root), IMAGE_FOLDER)
    target_parent_dir = os.path.join(OUTPUT_FOLDER, relative_path_to_parent)

    os.makedirs(target_parent_dir, exist_ok=True)

    output_file = os.path.join(target_parent_dir, f"{folder_name}.md")

    with open(output_file, "a", encoding="utf-8") as f:
        for index, img_file in enumerate(current_folder_photos):
            img_path = os.path.join(root, img_file)
            print(f"\n[{index+1}/{len(current_folder_photos)}] File in progress: {img_file}...")
            base64_image = encode_image(img_path)
            PROMPT_TEXT = "Перед тобою сторінка зі звіту університету.\
            Напиши весь текст, який ти бачиш на сторінці.\
            1. Якщо бачиш графіки — опиши їх словами або таблицею.\
            2. Якщо бачиш карту України - випиши цифри та назви областей.\
            3. Якщо немає ні графіків, ні карти України - не згадуй їх.\
            "

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPT_TEXT},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                )
                result_text = response.choices[0].message.content
                f.write(f"# Дані {img_file}\n{result_text}\n\n---\n\n")
                f.flush()
                time.sleep(2)

            except Exception as e:
                print(f"API ERROR: {e}")
                time.sleep(5)
