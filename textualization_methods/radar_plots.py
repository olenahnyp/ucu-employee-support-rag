"""
This file is used to creayed radar plots for textualizations to compare
LLM-as-a-Judge scores for different metrics for various methods.
"""
import os
from math import pi
import pandas as pd
import matplotlib.pyplot as plt

FILE_PATH = 'benchmark_results_free_approaches.xlsx'
df = pd.read_excel(FILE_PATH)

df = df[df['Model Judge'] == 'openai/gpt-4o'].copy()

categories = ['Avg Linguistic Score', 'Avg Structure Score', 'Avg Data Score']
N = len(categories)

angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]

colors = {
    'Google: Gemma 3 27B (free)': '#B19CD9',
    'LlamaParse': '#92B6E1',
    'LlamaParse Prompt': "#1C4583",
    'Google: Gemini 3 Flash Preview': '#4B0082',
    'Anthropic: Claude Opus 4.6': '#FF8C00',
    'Anthropic: Claude Sonnet 4.6': '#B3541E',
    'OpenAI: GPT-5.4': '#8E4585'
}

OUTPUT_DIR = 'plots'

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def create_radar_chart(category_name, data_subset):
    """
    This is the main function to create radar plots.
    """
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    plt.xticks(angles[:-1], ['Linguistic', 'Structure', 'Data'], color='black', size=12)

    ax.set_rlabel_position(0)
    ax.tick_params(axis='x', pad=25)
    plt.yticks([2, 4, 6, 8, 10], ["2", "4", "6", "8", "10"], color="grey", size=10)
    plt.ylim(0, 10)

    for i, row in data_subset.iterrows():
        method_name = row['Experiment Name']
        values = row[categories].tolist()
        values += values[:1] 
        color = colors.get(method_name, 'grey')  
        ax.plot(angles, values, linewidth=2, linestyle='solid', label=method_name, color=color)
        ax.fill(angles, values, color=color, alpha=0.1)

    plt.legend(loc='upper right', bbox_to_anchor=(0.1, 0.1))
    plt.title(f"{category_name[:-3]}", size=22, weight='bold', y=1.2)
    filename = f"chart_{category_name[:-3].lower().replace(' ', '_')}_free_approaches.png"
    save_path = os.path.join(OUTPUT_DIR, filename)
    plt.savefig(save_path, dpi=300, bbox_inches='tight')

input_types = df['Input File'].unique()

for input_type in input_types:
    subset = df[df['Input File'] == input_type]
    if input_type=="Simple text.md":
        input_type = "Standard text.md"
    elif input_type=="Visual data.md":
        input_type="Visual layouts.md"
    create_radar_chart(input_type, subset)
