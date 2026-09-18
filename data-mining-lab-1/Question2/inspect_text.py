import pandas as pd
import os
from pathlib import Path

question2_dir = Path(__file__).resolve().parent

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
        file_path = notices_dir / file
        df = pd.read_csv(file_path) if file.endswith('.csv') else pd.read_parquet(file_path)
        matches = df[df['notice_id'].isin(target_ids)]
        for _, row in matches.iterrows():
            texts[row['notice_id']] = str(row['body'])

print("--- SAME PAIR ---")
print(f"Notice {same_pair['notice_id_a']} length: {len(texts[same_pair['notice_id_a']])}")
print(texts[same_pair['notice_id_a']][:500])
print("\n")
print(f"Notice {same_pair['notice_id_b']} length: {len(texts[same_pair['notice_id_b']])}")
print(texts[same_pair['notice_id_b']][:500])

print("\n--- DIFFERENT PAIR ---")
print(f"Notice {diff_pair['notice_id_a']} length: {len(texts[diff_pair['notice_id_a']])}")
print(texts[diff_pair['notice_id_a']][:500])
print("\n")
print(f"Notice {diff_pair['notice_id_b']} length: {len(texts[diff_pair['notice_id_b']])}")
print(texts[diff_pair['notice_id_b']][:500])