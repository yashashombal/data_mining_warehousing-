import os
import shutil
import re
from pathlib import Path

script_dir = Path(__file__).resolve().parent
source_dir = script_dir / 'Question1' / 'sales'
target_dir = script_dir / 'partitioned_sales'

os.makedirs(target_dir, exist_ok=True)

# Updated regex to match SALES_S01_20240101.csv
# Group 1: Store (S01), Group 2: Year (2024), Group 3: Month (01)
pattern = re.compile(r'SALES_(S\d+)_(\d{4})(\d{2})\d{2}\.(csv|parquet)')

moved_count = 0

for filename in os.listdir(source_dir):
    match = pattern.search(filename)
    if match:
        store = match.group(1)
        year = match.group(2)
        month = match.group(3)
        
        # Create the nested folder path
        dest_path = os.path.join(target_dir, f'year={year}', f'month={month}', f'store={store}')
        os.makedirs(dest_path, exist_ok=True)
        
        # Copy the file into the new folder
        shutil.copy(os.path.join(source_dir, filename), os.path.join(dest_path, filename))
        moved_count += 1

print(f"Successfully organized {moved_count} files!")