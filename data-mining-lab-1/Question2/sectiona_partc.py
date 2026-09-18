import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import re
import os
import hashlib
from pathlib import Path
from collections import defaultdict

question2_dir = Path(__file__).resolve().parent
print("--- 1. Loading Data & Text Processing Pipeline ---")

# Clean text function (incorporating our robust cleaning rules)
def clean_text_pipeline(text):
    text = str(text)
    text = re.sub(r'\d+', '<NUM>', text)
    text = text.replace('NATIONAL PROCUREMENT AGGREGATION SERVICE', '')
    text = text.replace('STATE PROCUREMENT CELL', '')
    return text

def get_trigrams(text):
    text = str(text).lower()
    return set(text[i:i+3] for i in range(len(text)-2))

# Load notices from parquet / csv parts
notices_dir = question2_dir / 'notices'
all_notices = []

for file in os.listdir(notices_dir):
    if file.endswith('.parquet') or file.endswith('.csv') or file.endswith('.xlsx') or file.endswith('.xls'):
        filepath = notices_dir / file
        if file.endswith('.csv'):
            df = pd.read_csv(filepath)
        elif file.endswith('.parquet'):
            df = pd.read_parquet(filepath)
        else:
            # If Excel files from the folder screenshot
            df = pd.read_excel(filepath)
        all_notices.append(df[['notice_id', 'body']])

if not all_notices:
    raise FileNotFoundError(
        f'No notice files found in {notices_dir}. '
        'Restore the CSV, Parquet, or Excel notice parts before running this script.'
    )

notices_df = pd.concat(all_notices, ignore_index=True)
print(f"Loaded {len(notices_df)} notices successfully.")

print("\n--- 2. Computing MinHash Signatures (k=400) ---")
k = 400
def get_minhash_signature(tokens, k=400):
    if not tokens:
        return [float('inf')] * k
    base_hashes = np.array([
        int(hashlib.md5(token.encode('utf-8')).hexdigest()[:8], 16)
        for token in tokens
    ], dtype=np.int64)
    signature = []
    for index in range(k):
        hash_values = ((index + 1) * base_hashes + (index * 137)) % 2147483647
        signature.append(int(hash_values.min()))
    return signature

signatures = {}
for _, row in notices_df.iterrows():
    cleaned = clean_text_pipeline(row['body'])
    tokens = get_trigrams(cleaned)
    signatures[row['notice_id']] = get_minhash_signature(tokens, k)

print("MinHash signatures generated for all notices.")

print("\n--- 3. LSH Candidate Generation (b=20, r=20) ---")
b = 20
r = 20
candidates = set()

# Banding and bucket matching
for band_idx in range(b):
    buckets = defaultdict(list)
    start_idx = band_idx * r
    end_idx = (band_idx + 1) * r
    
    for notice_id, sig in signatures.items():
        # Extract the r rows for this band
        band_slice = tuple(sig[start_idx:end_idx])
        # Hash the band slice into a bucket key
        bucket_key = hashlib.md5(str(band_slice).encode('utf-8')).hexdigest()
        buckets[bucket_key].append(notice_id)
    
    # Generate candidate pairs from buckets with > 1 notice
    for bucket_key, members in buckets.items():
        if len(members) > 1:
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    pair = tuple(sorted([members[i], members[j]]))
                    candidates.add(pair)

print(f"Total candidate pairs generated via LSH: {len(candidates)}")
total_possible = (len(notices_df) * (len(notices_df) - 1)) / 2
print(f"Total possible pairs without LSH: {int(total_possible):,}")
print(f"Reduction factor: {100 * (1 - len(candidates) / total_possible):.2f}% fewer pairs to evaluate.")

print("\n--- 4. Plotting S-Curve & Operating Point ---")
def lsh_probability(s, b, r):
    return 1 - (1 - s**r)**b

s_range = np.linspace(0, 1, 300)
plt.figure(figsize=(8, 5))
plt.plot(s_range, lsh_probability(s_range, 20, 20), color='darkorange', linewidth=2.5, label='Selected Operating Point (b=20, r=20, Threshold ~0.86)')
plt.plot(s_range, lsh_probability(s_range, 50, 8), color='royalblue', linestyle='--', label='Alternative (b=50, r=8)')

plt.axvline(x=0.86, color='gray', linestyle=':', alpha=0.7)
plt.axhline(y=0.5, color='gray', linestyle=':', alpha=0.7)
plt.title('LSH Candidate Survival Probability & Operating Point')
plt.xlabel('True Jaccard Similarity (s)')
plt.ylabel('Probability of Surviving to Candidate Stage')
plt.legend(loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(question2_dir / 'lsh_operating_point.png', dpi=300)
print("Saved S-curve plot as 'lsh_operating_point.png'.")