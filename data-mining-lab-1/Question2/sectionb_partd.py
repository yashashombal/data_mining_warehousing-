import sqlite3
import time
import random

print("--- Initializing In-Memory SQLite Database for Benchmarking ---")
conn = sqlite3.connect(':memory:')
cursor = conn.cursor()

# 1. Create the Relational Schema
cursor.execute('''
CREATE TABLE notices (
    notice_id VARCHAR(32) PRIMARY KEY,
    portal_id VARCHAR(16) NOT NULL,
    published_at TIMESTAMP NOT NULL,
    estimated_value NUMERIC,
    closing_date TIMESTAMP,
    body TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE lsh_buckets (
    band_id INT NOT NULL,
    bucket_hash VARCHAR(32) NOT NULL,
    notice_id VARCHAR(32) REFERENCES notices(notice_id) ON DELETE CASCADE
)
''')
conn.commit()

# 2. Populate with simulated 12,000 notices and 240,000 LSH band rows (20 bands per notice)
print("Populating database with 12,000 notices and 240,000 LSH bucket rows...")
notices_data = [(f"N{i:06d}", f"P{random.randint(1, 260):03d}", "2026-01-01", 100000, "2026-12-31", "sample notice body text...") for i in range(12000)]
cursor.executemany("INSERT INTO notices VALUES (?, ?, ?, ?, ?, ?)", notices_data)

buckets_data = []
for i in range(12000):
    notice_id = f"N{i:06d}"
    for band_id in range(20):
        bucket_hash = f"hash_{band_id}_{random.randint(1, 500)}"
        buckets_data.append((band_id, bucket_hash, notice_id))

cursor.executemany("INSERT INTO lsh_buckets VALUES (?, ?, ?)", buckets_data)
conn.commit()

# Test query parameters
query = "SELECT notice_id FROM lsh_buckets WHERE band_id = ? AND bucket_hash = ?"
test_params = (5, "hash_5_123")

# --- 3. Benchmark Rejected Alternative: Forced Sequential Scan (No Index) ---
print("\n--- Running Rejected Alternative (Sequential Scan) ---")
cursor.execute(f"EXPLAIN QUERY PLAN {query}", test_params)
seq_plan = cursor.fetchall()

start_time = time.perf_counter()
for _ in range(50):
    cursor.execute(query, test_params).fetchall()
seq_time = (time.perf_counter() - start_time) / 50 * 1000 # in ms

print(f"Planner Path: {seq_plan}")
print(f"Wall-Clock Time: {seq_time:.4f} ms per query")

# --- 4. Benchmark Chosen Access Method: Composite B-Tree Index Seek ---
print("\n--- Running Chosen Access Method (B-tree Index Seek) ---")
cursor.execute("CREATE INDEX idx_lsh_band_bucket ON lsh_buckets (band_id, bucket_hash)")
conn.commit()

cursor.execute(f"EXPLAIN QUERY PLAN {query}", test_params)
indexed_plan = cursor.fetchall()

start_time = time.perf_counter()
for _ in range(1000):
    cursor.execute(query, test_params).fetchall()
indexed_time = (time.perf_counter() - start_time) / 1000 * 1000 # in ms

print(f"Planner Path: {indexed_plan}")
print(f"Wall-Clock Time: {indexed_time:.4f} ms per query")

print(f"\nSpeedup Factor: {seq_time / indexed_time:.1f}x faster with B-tree index!")
conn.close()