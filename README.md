# Data Mining and Warehousing Lab Exam

## Task Progress

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

```text
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
```

Run from `data-mining-lab-1/Question1`:

```powershell
py .\cross_system_query.py
```

