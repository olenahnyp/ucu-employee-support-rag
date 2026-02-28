"""
This code creates snapshots of all of the pages in pdf file.
"""
import os
import fitz

INPUT_FOLDER = "benchmark_dataset"
OUTPUT_FOLDER = "benchmark_dataset_snapshots"
ZOOM = 2

if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

for root, dirs, files in os.walk(INPUT_FOLDER):
    for file in files:
        full_path = os.path.join(root, file)
        relative_path = os.path.relpath(root, INPUT_FOLDER)
        target_dir = os.path.join(OUTPUT_FOLDER, relative_path, file[:-4])
        os.makedirs(target_dir, exist_ok=True)
        pdf_file = fitz.open(full_path)
        print(f"Total number of pages in the file: {len(pdf_file)}")

        for page_index, page in enumerate(pdf_file):
            print(f"Page {page_index + 1} in progress...")
            mat = fitz.Matrix(ZOOM, ZOOM)
            pix = page.get_pixmap(matrix=mat)
            filename = f"page_{page_index + 1}_full.png"
            filepath = os.path.join(target_dir, filename)
            pix.save(filepath)

print(f"Done! Images saved in the folder: '{OUTPUT_FOLDER}'")
