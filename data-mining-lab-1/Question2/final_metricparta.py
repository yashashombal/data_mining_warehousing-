import pandas as pd
import re
import os
from pathlib import Path

question2_dir = Path(__file__).resolve().parent

# --- 1. Define Functions ---
def get_jaccard_similarity(set1, set2):
    if not set1 and not set2: return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))

def get_trigrams(text):
    text = str(text).lower()
    return set(text[i:i+3] for i in range(len(text)-2))

def clean_text_pipeline(text):
    text = str(text)
    # Mask variable entities (dates, money, references)
    text = re.sub(r'\d+', '<NUM>', text)
    # Strip known nodal boilerplate noise
    text = re.sub(r'(?i).*NATIONAL PROCUREMENT AGGREGATION SERVICE.*', '', text, flags=re.DOTALL)
    text = re.sub(r'(?i).*STATE PROCUREMENT CELL.*', '', text, flags=re.DOTALL)
    return text

# --- 2. Load Data ---
labels = pd.read_csv(question2_dir / 'labelled_pairs.csv')
same_pair = labels[labels['label'] == 'same'].iloc[0]
diff_pair = labels[labels['label'] == 'different'].iloc[0]

target_ids = {
    same_pair['notice_id_a'], same_pair['notice_id_b'],
    diff_pair['notice_id_a'], diff_pair['notice_id_b']
}

texts = {}
notices_dir = question2_dir / 'notices'
for file in os.listdir(notices_dir):
    if file.endswith('.parquet') or file.endswith('.csv'):
        filepath = notices_dir / file
        # Handle both CSV and Parquet depending on how your files are actually saved
        df = pd.read_csv(filepath) if file.endswith('.csv') else pd.read_parquet(filepath)
        
        matches = df[df['notice_id'].isin(target_ids)]
        for _, row in matches.iterrows():
            texts[row['notice_id']] = str(row['body'])

# --- 3. Evaluate Metrics ---
print("--- Choice 1: Raw Text Comparison ---")
raw_same = get_jaccard_similarity(get_trigrams(texts[same_pair['notice_id_a']]), get_trigrams(texts[same_pair['notice_id_b']]))
raw_diff = get_jaccard_similarity(get_trigrams(texts[diff_pair['notice_id_a']]), get_trigrams(texts[diff_pair['notice_id_b']]))
print(f"Same Pair Score: {raw_same:.3f}")
print(f"Diff Pair Score: {raw_diff:.3f}")

print("\n--- Choice 2: Cleaned Text Comparison (Adopted) ---")
clean_same = get_jaccard_similarity(get_trigrams(clean_text_pipeline(texts[same_pair['notice_id_a']])), 
                                    get_trigrams(clean_text_pipeline(texts[same_pair['notice_id_b']])))
clean_diff = get_jaccard_similarity(get_trigrams(clean_text_pipeline(texts[diff_pair['notice_id_a']])), 
                                    get_trigrams(clean_text_pipeline(texts[diff_pair['notice_id_b']])))
print(f"Same Pair Score: {clean_same:.3f}")
print(f"Diff Pair Score: {clean_diff:.3f}")