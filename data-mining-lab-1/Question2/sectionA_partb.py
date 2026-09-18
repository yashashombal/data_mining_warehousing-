import pandas as pd
import re
import os
import hashlib
from pathlib import Path

question2_dir = Path(__file__).resolve().parent

# --- 1. Clean & Tokenize ---
def clean_text_pipeline(text):
    text = str(text)
    text = re.sub(r'\d+', '<NUM>', text)
    # Exact string replacements for nodal boilerplate
    text = text.replace('NATIONAL PROCUREMENT AGGREGATION SERVICE', '')
    text = text.replace('STATE PROCUREMENT CELL', '')
    return text

def get_trigrams(text):
    text = str(text).lower()
    return set(text[i:i+3] for i in range(len(text)-2))

# --- 2. Similarity Functions ---
def exact_jaccard(set1, set2):
    if not set1 and not set2: return 0.0
    return len(set1.intersection(set2)) / len(set1.union(set2))

def get_minhash_signature(tokens, k=400):
    signature = [float('inf')] * k
    for token in tokens:
        # Generate a stable base hash for the token using MD5
        base_hash = int(hashlib.md5(token.encode('utf-8')).hexdigest()[:8], 16)
        for i in range(k):
            # Generate k independent hash values using a linear congruential generator
            hash_val = ((i + 1) * base_hash + (i * 137)) % 2147483647
            if hash_val < signature[i]:
                signature[i] = hash_val
    return signature

def minhash_jaccard(sig1, sig2):
    matches = sum(1 for i, j in zip(sig1, sig2) if i == j)
    return matches / len(sig1)

# --- 3. Load Data ---
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
        df = pd.read_csv(filepath) if file.endswith('.csv') else pd.read_parquet(filepath)
        matches = df[df['notice_id'].isin(target_ids)]
        for _, row in matches.iterrows():
            texts[row['notice_id']] = str(row['body'])

# --- 4. Measure Realized Error ---
print(f"Target Predicted Error Margin: ±5.0%\n")

for pair_name, p in [("SAME PAIR", same_pair), ("DIFFERENT PAIR", diff_pair)]:
    t1 = get_trigrams(clean_text_pipeline(texts[p['notice_id_a']]))
    t2 = get_trigrams(clean_text_pipeline(texts[p['notice_id_b']]))
    
    exact_score = exact_jaccard(t1, t2)
    
    sig1 = get_minhash_signature(t1, k=400)
    sig2 = get_minhash_signature(t2, k=400)
    est_score = minhash_jaccard(sig1, sig2)
    
    error = abs(exact_score - est_score) * 100
    
    print(f"--- {pair_name} ---")
    print(f"Exact Jaccard:     {exact_score:.4f}")
    print(f"MinHash Estimated: {est_score:.4f}")
    print(f"Realized Error:    {error:.2f}%\n")