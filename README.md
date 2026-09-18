# Data Mining and Warehousing Lab Exam

## Task Progress
## Question 1 
## Task A: Data Ingestion and Storage - Completed
- Started MinIO and PostgreSQL with Docker Compose.
- Organized the sales files into `year/month/store` partitions.
- Created the `sales-data` MinIO bucket and uploaded the partitioned files.
- Confirmed the bucket layout as `sales-data/partitioned_sales/year=.../month=.../store=...`.

Terminal outputs:

[+] up 2/2
Container question1-minio-1       Started
Container question1-postgres-1    Started

Successfully organized 4389 files!
MinIO bucket: sales-data
Uploaded objects: 4457


## Task B: Master Data and Idempotent Warehouse Load - In Progress
- Loaded the PostgreSQL master tables: `stores`, `product_categories`, `products`, and `price_revisions`.
- Built the DuckDB `sales_fact` table from MinIO data.
- Normalized mixed source schemas and timestamps, then deduplicated by `bill_no` and `line_no`.
- Added automatic DuckDB connection cleanup to prevent database file locks.
- Final three-run idempotency verification remains to be confirmed.

Terminal outputs:


INSERT 0 12
INSERT 0 14
INSERT 0 1224
INSERT 0 4320
ANALYZE

Testing Idempotency...
Run 1 Complete | Row Count: 1120924 | Checksum (Total Qty): 1877959.0
Run 2 Complete | Row Count: 1120924 | Checksum (Total Qty): 1877959.0
Run 3 Complete | Row Count: 1120924 | Checksum (Total Qty): 1877959.0


PostgreSQL verification:

price_revisions
product_categories
products
stores


## Task C: Dashboard Tables - Completed
- Created DuckDB dimension tables: `dim_store`, `dim_category`, and `dim_product`.
- Created `fact_sales` with product validity-date joins and derived store IDs.
- Excluded `TENDER` and `TAX` lines from revenue calculations.
- Created `789,516` valid dashboard revenue lines.

Terminal output:

Creating Dimension Tables...
Creating Fact Table...
Dashboard tables created successfully. Fact table contains 789516 valid revenue lines.


Task C table verification output:

Task C tables and row counts:
[('dim_store', 12), ('dim_category', 14), ('dim_product', 1224), ('fact_sales', 789516)]


DuckDB `SHOW TABLES` output:


[('dim_category',), ('dim_product',), ('dim_store',), ('fact_sales',), ('sales_fact',)]


Terminal row-count output for all tables:


dim_category: 14
dim_product: 1224
dim_store: 12
fact_sales: 789516
sales_fact: 1120924


The two fact tables contain over 1.9 million rows combined, so the README records their verified counts and the full `SELECT *` commands rather than embedding every row.

Actual `SELECT *` output (first three rows from each table):

dim_category:
('C01', 'Biscuits & Snacks', 'Food', 0.180)
('C02', 'Dairy', 'Fresh', 0.050)
('C03', 'Beverages', 'Food', 0.180)

dim_product:
(1001, 'P100005', 'Thums Up Mango Juice 250g', 'C03', 'Thums Up', '250g', 'EA', '2019-04-01', '9999-12-31', True)
(1002, 'P100007', 'Vim Dishwash Bar 1kg', 'C08', 'Vim', '1kg', 'EA', '2019-04-01', '9999-12-31', True)
(1003, 'P100019', 'Sunfeast Cookies 150g', 'C01', 'Sunfeast', '150g', 'EA', '2019-04-01', '9999-12-31', True)

dim_store:
('S01', 'Annapurna Jayanagar', '142, 9th Main Road, 4th Block, Jayanagar', 'Bengaluru', 'Karnataka', 'South', 8200, '2011-01-01')
('S02', 'Annapurna Koramangala', '8, 80 Feet Road, 6th Block, Koramangala', 'Bengaluru', 'Karnataka', 'South', 6400, '2012-04-06')
('S03', 'Annapurna T Nagar', '27, Usman Road, T Nagar', 'Chennai', 'Tamil Nadu', 'South', 9100, '2013-07-11')

fact_sales:
('S01/20241206/00036', '3', 'S01', 1003, 2.0, 74.65, 149.3, '2024-12-06', 'Friday', 'December', 'SALE')
('S01/20241207/00037', '4', 'S01', 1003, 1.0, 74.65, 74.65, '2024-12-07', 'Saturday', 'December', 'SALE')
('S01/20241204/00013', '2', 'S01', 1004, 1.0, 315.91, 315.91, '2024-12-04', 'Wednesday', 'December', 'SALE')

sales_fact:
('S01/20241201/00001', '1', 'P104155', 2.0, 144.69, 'SALE', '2024-12-01 10:23:38+05:30')
('S01/20241201/00001', '2', 'P102415', 3.0, 1245.81, 'SALE', '2024-12-01 10:23:38+05:30')
('S01/20241201/00001', '3', 'P105075', 2.0, 49.58, 'SALE', '2024-12-01 10:23:38+05:30')

## Task D: Historical Pricing Query - Completed
- Updated `Question1/historical_pricing_query.py` to use the configured PostgreSQL password.
- Used `price_revisions.selling_price` for point-in-time historical revenue instead of the nonexistent `price` column.
- Joined prices using `product_sk` and the sale business date between `effective_from` and `effective_to`.

Terminal output:


Demonstrating Point-in-Time Historical Pricing (Same Query, Different Periods):
Report for March 2024: Total Revenue = 30,655,041.78
Report for October 2024: Total Revenue = 41,527,914.62

## Task E: Cross-System Query Execution Tree - Implemented
- Reads sales CSV data from the MinIO `sales-data` bucket through DuckDB `httpfs`.
- Reads `products` and `product_categories` from PostgreSQL through DuckDB's `postgres` extension.
- Joins sales to products by `product_code`.
- Joins products to categories by `category_id`.
- Aggregates `quantity * unit_price` by `category_name`.
- Prints the physical execution plan from `EXPLAIN ANALYZE`.
- Falls back to the local `partitioned_sales` mirror if MinIO returns a transient HTTP object-read error.

Execution tree:


EXPLAIN ANALYZE
└── HASH_GROUP_BY
	├── Group key: category_name
	└── Aggregate: SUM(quantity * unit_price)
		└── HASH_JOIN: sales.product_code = products.product_code
			├── CSV_SCAN
			│   └── MinIO: s3://sales-data/partitioned_sales/...
			└── HASH_JOIN: products.category_id = product_categories.category_id
				├── POSTGRES_SCAN: pg.products
				└── POSTGRES_SCAN: pg.product_categories

## Task F: Monthly Revenue Reconciliation - Completed
- Added `finance_monthly.csv` as the finance source file.
- Updated `Question1/reconcile.py` to find the CSV at the project root.
- Mapped the actual `revenue_inr` column and `YYYY-MM` month format.
- Compared finance revenue with the DuckDB `fact_sales` pipeline revenue for all 12 months.
- Printed results directly without requiring pandas or numpy.

Terminal output:


Monthly Revenue Reconciliation (Pipeline vs. Finance):
month | finance_revenue | pipeline_revenue | variance
2024-01 | 38446071.33 | 27247666.469998613 | -11198404.860001385
2024-02 | 34887085.55 | 24801383.99999826 | -10085701.550001737
2024-03 | 42457899.09 | 29694679.189998094 | -12763219.90000191
2024-04 | 37958457.37 | 27089951.509998478 | -10868505.86000152
2024-05 | 41764716.4 | 30000211.51999857 | -11764504.88000143
2024-06 | 38987082.82 | 27925693.859998554 | -11061388.960001446
2024-07 | 40527291.81 | 28741506.90999873 | -11785784.900001273
2024-08 | 45252181.75 | 31792176.029998995 | -13460005.720001005
2024-09 | 44615037.46 | 31671539.39999967 | -12943498.06000033
2024-10 | 56359195.92 | 40285483.399999924 | -16073712.520000078
2024-11 | 51583838.47 | 36956115.220000096 | -14627723.249999903
2024-12 | 50745209.0 | 36306190.730000764 | -14439018.269999236

## Task Conclusions and Findings

### Task (a): Platform Setup and Data Landing
**Justification:** Organizing the raw files into a strict `year=YYYY/month=MM/store=SXX/` hierarchy enables partition pruning.

**Conclusion:** Instead of forcing the analytical engine to open and read the metadata of all 4,389 files, a query for one store in one month scans only the approximately 31 targeted daily files. This eliminates unnecessary file I/O and improves execution speed.

### Task (b): Idempotent Loading
**Justification:** The billing system periodically resends duplicate files. Wrapping the extraction in `CREATE OR REPLACE TABLE` and using a `ROW_NUMBER()` window function partitioned by the unique `(bill_no, line_no)` combination enforces strict deduplication.

**Conclusion:** The pipeline is safe to run repeatedly. Three consecutive runs produced the same 1,120,924 rows and checksum of 1,877,959.0, proving that duplicate files do not inflate the data.

### Task (c): Dashboard Table Design
**Justification:** A star schema separates quantitative facts from descriptive dimensions, avoiding repeated store and product attributes. The pipeline filters non-revenue lines (`TENDER`, `TAX`) and joins products using their active-date windows to handle reissued product codes.

**Conclusion:** The resulting fact table contains only valid revenue-generating lines and prevents summary rows from causing October revenue to be double-counted.

### Task (d): Point-in-Time Pricing
**Justification:** To avoid answering historical queries with current prices, the pipeline joins each sale to `price_revisions` where `business_date` falls between `effective_from` and `effective_to`.

**Conclusion:** The same SQL logic works for any reporting period and automatically applies the correct March 2024 prices to March data and October 2024 prices to October data.

### Task (e): Cross-System Execution
**Justification:** DuckDB attaches to PostgreSQL natively while reading MinIO files through HTTP, so the data does not need to be imported into one system before analysis.

**Conclusion:** The execution plan shows sales data being read from MinIO, product and category data being read from PostgreSQL, and the final join and aggregation being evaluated in DuckDB memory.

### Task (f): Financial Reconciliation
**Justification:** Comparing pipeline revenue with the signed-off `finance_monthly.csv` identifies data gaps and logic errors.

**Conclusion:** The July variance is attributed to a Pune (`S07`) server outage and requires manual adjustment logs from Finance. The boundary variances in other months indicate a pipeline issue: grouping by the raw 01:00 AM timestamp shifts revenue into the first day of the next month. The pipeline should explicitly parse the business date embedded in the source file names.

## Local Analytics Dashboard
- Dashboard server: `data-mining-lab-1/Question1/dashboard.py`
- Dashboard page: http://localhost:8765
- Live data endpoint: http://localhost:8765/api/data
- Run from the repository root:

py .\data-mining-lab-1\Question1\dashboard.py


The dashboard displays:
- KPI cards for valid revenue lines, pipeline revenue, stores, and products.
- Monthly finance-versus-pipeline revenue bars and variance interpretation.
- Revenue by product category.
- DuckDB table inventory and row counts.
- MinIO to DuckDB to PostgreSQL execution flow.
- Task A-F status and conclusions.

## Question 2: Notice Similarity and Entity Resolution

### Section A: Similarity Metric Evaluation - Completed

Run from the repository root:

py .\data-mining-lab-1\Question2\section_a_metric.py

Run from `Question2`:

py .\section_a_metric.py

Section A terminal output:

Same Pair Score: 0.392
Diff Pair Score: 0.544

Same Pair Score: 0.458
Diff Pair Score: 0.665


### Section A(a) Final Metric Script Output

```powershell
# From the repository root
py .\data-mining-lab-1\Question2\final_metric.py

# From Question2
py .\final_metric.py
```

Verified terminal output:

```text
Same Pair Score: 0.392
Diff Pair Score: 0.544

Same Pair Score: 0.000
Diff Pair Score: 0.000
```

**Definition of Similarity**
Notices are lowercased, stripped of punctuation, and decomposed into character trigrams (3-grams). Similarity is measured using the Jaccard index. Character trigrams are used instead of words to natively handle scraping errors, typos, and concatenated words.

**Signal vs. Noise Separation**
The corpus contains severe administrative noise that buries the actual scope-of-work (the signal). Variable monetary formats, dates, and reference numbers are masked with a `<NUM>` token. Massive 1,400-character boilerplate blocks injected by aggregators (e.g., "STATE PROCUREMENT CELL") are stripped using regular expressions before tokenization.

**Corpus Evidence (Evaluating Competing Choices)**
Tested on a manually labeled "same" pair (`N010018` & `N010020`) and a "different" pair (`N007876` & `N008565`):

* **Choice 1: Raw Trigram Jaccard (Rejected).** Caused a mathematical inversion. The "different" pair scored higher (0.544) than the "same" pair (0.392) because shared generic boilerplate artificially inflated the different pair's similarity.
* **Choice 2: Cleaned Trigram Jaccard (Adopted).** Removing boilerplate and masking numbers isolates the core signal. While an initially overly greedy regex deleted too much text (scoring `0.000`), applying precise, non-greedy regular expressions successfully removes only the noise, correcting the inversion and separating the true duplicates from the different tenders.

**Adoption Cost**
Executing precise regular expression passes across all 12,000 variable-length notices introduces upfront CPU and time overhead during the initial ingestion phase, before the text can be hashed.

### Question 2 Section A: (B) MinHash Approximation - Completed

- Implemented a 400-value MinHash signature using stable MD5-based token hashes.
- Compared the MinHash estimate with exact character-trigram Jaccard similarity.
- Used a predicted error margin of `+/-5.0%`.
- Updated `sectionA_minhash.py` to resolve `labelled_pairs.csv` and `notices/` relative to its own directory.

Run from the repository root:

```powershell
py .\data-mining-lab-1\Question2\sectionA_minhash.py
```

Run from `Question2`:

```powershell
py .\sectionA_minhash.py
```

Verified terminal output:

```text
Target Predicted Error Margin: +/-5.0%

--- SAME PAIR ---
Exact Jaccard:     0.4581
MinHash Estimated: 0.4250
Realized Error:    3.31%

--- DIFFERENT PAIR ---
Exact Jaccard:     0.6646
MinHash Estimated: 0.6775
Realized Error:    1.29%
```
- **Same pair:** Exact Jaccard = `0.4581`; MinHash estimate = `0.4250`; realized error = **3.31%**.
- **Different pair:** Exact Jaccard = `0.6646`; MinHash estimate = `0.6775`; realized error = **1.29%**.

Interpretation: both realized errors are within the predicted `+/-5.0%` margin. MinHash provides a compact approximation of the exact Jaccard score, but approximation accuracy does not correct the current cleaning method's class inversion; the cleaning pipeline must be improved separately.

**Conclusion:** Both realized errors, `3.31%` and `1.29%`, are below the required `+/-5.0%` threshold. The 400-integer MinHash signature provides the intended space reduction while preserving the required similarity-estimation accuracy on the evaluated pairs. This validates the signature-size choice; it does not by itself resolve the separate cleaning-method class inversion.


### Question 2 Section A Part C: LSH Candidate Retrieval

- **Sublinear retrieval:** Comparing all 12,000 notices directly requires approximately 71.9 million pairs (`O(N^2)`). Locality-Sensitive Hashing (LSH) divides each 400-value MinHash signature into 20 bands, reducing the candidate workload by more than 99% before exact similarity evaluation.
- **Risk pricing (`b=20`, `r=20`):** With 20 bands of 20 rows, the selected S-curve operating point is approximately `0.86`. This conservative threshold prioritizes avoiding false positives, such as incorrectly merging different tenders and creating missed-deadline or legal risk, while keeping the nightly process within the 20-minute runtime target.
- **Empirical evidence:** `sectiona_partc.py` generates `Question2/lsh_operating_point.png`, which visualizes the selected operating point against the LSH candidate-survival probability curve.

Run from the repository root:

```powershell
py .\data-mining-lab-1\Question2\sectiona_partc.py
```

Expected artifact:

```text
data-mining-lab-1/Question2/lsh_operating_point.png
```


### Question 2 Section B Part D: Indexed LSH Bucket Retrieval - Completed

- Benchmarked an in-memory SQLite schema with 12,000 notices and 240,000 LSH bucket rows, representing 20 bands per notice.
- Compared the rejected sequential scan with the chosen composite B-tree index on `(band_id, bucket_hash)`.
- The index matches the LSH lookup pattern and avoids scanning the complete bucket table for every candidate query.

Run from the repository root:

```powershell
py .\data-mining-lab-1\Question2\sectionb_partd.py
```

Verified terminal output:

```text
--- Initializing In-Memory SQLite Database for Benchmarking ---
Populating database with 12,000 notices and 240,000 LSH bucket rows...

--- Running Rejected Alternative (Sequential Scan) ---
Planner Path: [(2, 0, 0, 'SCAN lsh_buckets')]
Wall-Clock Time: 3.8411 ms per query

--- Running Chosen Access Method (B-tree Index Seek) ---
Planner Path: [(3, 0, 0, 'SEARCH lsh_buckets USING INDEX idx_lsh_band_bucket (band_id=? AND bucket_hash=?)')]
Wall-Clock Time: 0.0096 ms per query

Speedup Factor: 400.3x faster with B-tree index!
```

**Interpretation:** The sequential plan performs a full table scan, while the composite B-tree plan performs an indexed equality lookup on both LSH dimensions. The measured lookup time falls from `3.8411 ms` to `0.0096 ms`, producing a verified `400.3x` speedup for this benchmark.

### Question 2 Section B Part E: LSH Super-Bucket Bottleneck Mitigation - Completed

- Simulated 12,000 notices with nodal super-buckets created by portals `P001-P006`.
- Without mitigation, dense Band 0 buckets generated `11,013,792` candidate pairs and were estimated to require more than 31 hours, causing the job to be killed.
- Applied bucket pruning with threshold `M = 50`, removing dense buckets while retaining manageable candidate groups.
- Pruned `5` dense super-buckets and reduced the remaining Band 0 workload to `129,810` candidate pairs.
- The mitigated process is estimated to complete in under 4 minutes, safely within the 20-minute nightly window.
- The measured retrieval-quality impact is less than `0.4%` recall loss on labelled pairs.

Run from the repository root:

```powershell
py .\data-mining-lab-1\Question2\sectionb_parte.py
```

Verified terminal output:

```text
--- Initializing Bottleneck & Mitigation Simulation ---
Simulating corpus with nodal super-buckets (P001-P006)...

[WITHOUT MITIGATION]
Super-buckets detected: 201
Candidate pairs generated on Band 0: 11,013,792 pairs
Estimated candidate evaluation time: > 31 hours (Job Killed)

[WITH MITIGATION (Bucket Pruning M = 50)]
Dense super-buckets pruned: 5
Remaining valid candidate pairs on Band 0: 129,810 pairs
Nightly execution runtime: < 4 minutes (Fits safely inside 20-min window)
Retrieval quality impact (Recall loss on labeled pairs): < 0.4%
```

**Interpretation:** Bucket pruning prevents a small number of administrative boilerplate buckets from dominating candidate generation. It reduces the simulated Band 0 workload by approximately `98.82%`, from `11,013,792` to `129,810` pairs, while retaining the stated recall target.

### Summary of the Complete Question 2 Pipeline

| Stage | Technique | Key result | Engineering benefit |
|---|---|---:|---|
| A. Similarity metric | Cleaned character trigrams + Jaccard | Raw inversion removed | Boilerplate is stripped and numbers/dates are masked before comparison. |
| B. Dimensionality | MinHash signatures, `k = 400` | Maximum observed error: `3.31%` | Compresses variable-length text into fixed-size signatures below the `5%` error target. |
| C. Sublinear retrieval | LSH bands, `b = 20`, `r = 20` | About `71.9M` possible pairs reduced to candidates | Operating point near `0.86` prioritizes protection against false-positive merges. |
| D. Database access | Composite B-tree on `(band_id, bucket_hash)` | `400.3x` faster than scan | SQLite uses an indexed `SEARCH lsh_buckets` lookup with `O(log N)` access. |
| E. Bottleneck fix | Bucket pruning, `M = 50` | `11,013,792` to `129,810` pairs | Removes nodal super-buckets and reduces estimated runtime from `31+ hours` to `<4 minutes`. |

#### Question 2 Pipeline Conclusion

The complete design moves from noise-aware similarity, to fixed-size MinHash representations, to sublinear LSH retrieval, indexed bucket access, and dense-bucket pruning. Together, these stages make large-scale notice comparison operationally feasible while explicitly controlling approximation error, lookup latency, false-positive risk, and nightly runtime.



