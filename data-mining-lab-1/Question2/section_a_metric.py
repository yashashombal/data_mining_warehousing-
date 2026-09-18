import pandas as pd
import os
import re
from pathlib import Path

question2_dir = Path(__file__).resolve().parent

# 1. Load the manual labels
labels = pd.read_csv(question2_dir / 'labelled_pairs.csv')

# 2. Sample one pair of each class
same_pair = labels[labels['label'] == 'same'].iloc[0]
diff_pair = labels[labels['label'] == 'different'].iloc[0]

target_ids = {
    same_pair['notice_id_a'], same_pair['notice_id_b'],
    diff_pair['notice_id_a'], diff_pair['notice_id_b']
}

# 3. Retrieve texts from the Parquet files
notices_dir = question2_dir / 'notices'
texts = {}
for file in os.listdir(notices_dir):
    if file.endswith('.parquet') or file.endswith('.csv'): # based on your folder image
        # Read file (adjust to pd.read_csv if they are actually CSVs despite the prompt saying parquet)
        file_path = notices_dir / file
        df = pd.read_csv(file_path) if file.endswith('.csv') else pd.read_parquet(file_path)
        
        matches = df[df['notice_id'].isin(target_ids)]
        for _, row in matches.iterrows():
            texts[row['notice_id']] = str(row['body'])

# 4. Define our two competing similarity functions
def get_trigrams(text):
    text = text.lower()
    return set(text[i:i+3] for i in range(len(text)-2))

def jaccard(set1, set2):
    if not set1 and not set2: return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))

def clean_text(text):
    # Strip known boilerplate
    text = text.replace('NATIONAL PROCUREMENT AGGREGATION SERVICE', '')
    text = text.replace('STATE PROCUREMENT CELL', '')
    
    # Mask numbers, dates, and money (replace digits with a standard token)
    text = re.sub(r'\d+', '<NUM>', text)
    return text

# 5. Evaluate Method 1: Raw Text
raw_same_score = jaccard(get_trigrams(texts[same_pair['notice_id_a']]), get_trigrams(texts[same_pair['notice_id_b']]))
raw_diff_score = jaccard(get_trigrams(texts[diff_pair['notice_id_a']]), get_trigrams(texts[diff_pair['notice_id_b']]))

# 6. Evaluate Method 2: Cleaned Text
clean_same_score = jaccard(get_trigrams(clean_text(texts[same_pair['notice_id_a']])), 
                           get_trigrams(clean_text(texts[same_pair['notice_id_b']])))
clean_diff_score = jaccard(get_trigrams(clean_text(texts[diff_pair['notice_id_a']])), 
                           get_trigrams(clean_text(texts[diff_pair['notice_id_b']])))

print(f"--- Choice 1: Raw Trigrams ---")
print(f"Same Pair Score: {raw_same_score:.3f}")
print(f"Diff Pair Score: {raw_diff_score:.3f}")

print(f"\n--- Choice 2: Cleaned Trigrams (Adopted) ---")
print(f"Same Pair Score: {clean_same_score:.3f}")
print(f"Diff Pair Score: {clean_diff_score:.3f}")