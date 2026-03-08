"""
LLM-as-a-Judge for textualization methods.
"""
import io
import base64
import json
import os
import glob
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

JUDGE_MODEL = "openai/gpt-4o"

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

def evaluate_summary_append(markdown_file, images_folder, experiment_name, output_excel="benchmark_results.xlsx"):
    """
    This function evaluates textualization of a particular file based on one of the
    textualization methods.
    """
    image_files = sorted(glob.glob(os.path.join(images_folder, "*.png")))
    with open(markdown_file, "r", encoding="utf-8") as f:
        full_markdown_text = f.read()

    scores = {
        "linguistic": [],
        "structure": [],
        "data": [],
        "all_justifications": []
    }

    for i, img_path in enumerate(image_files):
        filename = os.path.basename(img_path)
        print(f"[{i+1}/{len(image_files)}] {filename} in progress\n", end="", flush=True)

        base64_img = encode_image(img_path)

        prompt = f"""
            Ти — професійний аудитор якості даних. Твоє завдання: порівняти картинку (оригінальна сторінка звіту) з наданим текстом (результат розпізнавання).

            Оціни результат за шкалою від 1 до 10 за такими критеріями:
            1. linguistic_score: правильність слів, відсутність одруківок, якість української мови.
            2. structure_score: чи правильно відтворено заголовки, списки та абзаци.
            3. data_score: точність цифр у таблицях та описів графіків з картинок, а також відповідність прізвищ.

            Текст для аналізу (Markdown):
            {full_markdown_text[:20000]}... 

            ВАЖЛИВО: Дай відповідь ТІЛЬКИ у форматі JSON. Не пиши жодних вступних слів чи пояснень поза структурою JSON.
            Приклад відповіді:
            {{
            "linguistic_score": оцінка від 1 до 10,
            "structure_score": оцінка від 1 до 10,
            "data_score": оцінка від 1 до 10,
            "justification": "Коротке пояснення українською мовою: що саме модель зробила добре, а де помилилася."
            }}
            """

        try:
            response = client.chat.completions.create(
                model=JUDGE_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": 
                            {"url": f"data:image/jpeg;base64,{base64_img}"}},
                        ],
                    }
                ],
            ) 
            raw_text = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
            try:
                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                result = json.loads(raw_text[start:end])
                scores["linguistic"].append(result.get("linguistic_score", 0))
                scores["structure"].append(result.get("structure_score", 0))
                scores["data"].append(result.get("data_score", 0))
                if result.get("justification"):
                    scores["all_justifications"].append(f"{filename}: {result['justification']}")             
            except:
                print("JSON ERROR")
                continue

        except Exception as e:
            print(f"API ERROR: {e}")
            continue

    full_justification_text = "\n".join(scores["all_justifications"])

    summary_prompt = f"""
    На основі окремих зауважень по кожній сторінці текстуалізації {experiment_name}, 
    напиши один загальний синтезований висновок (до 2-3 речень) про якість роботи моделі.
    Зверни увагу на повторювані помилки або навпаки — на те, що стабільно виходило добре.

    Окремі зауваження:
    {full_justification_text}
    """

    summary_response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    final_justification = summary_response.choices[0].message.content.strip()

    avg_linguistic = round(sum(scores["linguistic"]) / len(scores["linguistic"]), 2)
    avg_structure = round(sum(scores["structure"]) / len(scores["structure"]), 2)
    avg_data = round(sum(scores["data"]) / len(scores["data"]), 2)

    new_row = {
        "Experiment Name": experiment_name,
        "Input File": os.path.basename(markdown_file),
        "Avg Linguistic Score": avg_linguistic,
        "Avg Structure Score": avg_structure,
        "Avg Data Score": avg_data,
        "Justification": final_justification,
        "Pages Processed": len(scores["linguistic"]),
        "Model Judge": JUDGE_MODEL
    }

    df_new = pd.DataFrame([new_row])

    try:
        if os.path.exists(output_excel):
            df_old = pd.read_excel(output_excel)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df_final = df_new

        df_final.to_excel(output_excel, index=False)
        print("Results were saved to Excel file")      
    except PermissionError:
        print(f"File is open in Excel")

evaluate_summary_append(
    markdown_file="benchmark_dataset_llamaparse_with_prompt/Visual data.md",
    images_folder="benchmark_dataset_snapshots/Visual data",
    experiment_name="LlamaParse Prompt"
)
