import duckdb
from pathlib import Path

def run_load(run_number):
    # Connect to a persistent local DuckDB file (this will act as our query engine cache)
    with duckdb.connect('annapurna.duckdb') as con:
        # 1. Configure the connection to your local MinIO object store
        con.execute("""
            INSTALL httpfs;
            LOAD httpfs;
            SET threads = 1;
            DROP SECRET IF EXISTS minio_secret;
            CREATE SECRET minio_secret (
                TYPE S3,
                KEY_ID 'admin',
                SECRET 'password',
                REGION 'us-east-1',
                ENDPOINT 'localhost:9000',
                URL_STYLE 'path',
                USE_SSL false
            );
        """)

        local_partitioned_sales = Path(__file__).resolve().parent / 'partitioned_sales'
        csv_files = [
            's3://sales-data/partitioned_sales/' + path.relative_to(local_partitioned_sales).as_posix()
            for path in local_partitioned_sales.rglob('*.csv')
        ]
        if not csv_files:
            raise FileNotFoundError(f'No CSV files found in {local_partitioned_sales}')
        csv_file_list = ', '.join("'" + path.replace("'", "''") + "'" for path in csv_files)
        source_queries = [
            f"""
            SELECT bill_no, line_no,
                   COALESCE(product_code, item_code) AS product_code,
                   TRY_CAST(COALESCE(qty, quantity) AS DOUBLE) AS quantity,
                   TRY_CAST(COALESCE(unit_price, rate) AS DOUBLE) AS unit_price,
                   COALESCE(line_type, type) AS line_type,
                   CASE
                       WHEN regexp_matches(COALESCE(ts, txn_time), '^[0-9]+$')
                           THEN to_timestamp(TRY_CAST(COALESCE(ts, txn_time) AS BIGINT))
                       ELSE TRY_CAST(COALESCE(ts, txn_time) AS TIMESTAMP)
                   END AS timestamp
            FROM read_csv_auto([{csv_file_list}], union_by_name = true, all_varchar = true)
            """
        ]

        # 2. Execute the idempotent load using CREATE OR REPLACE
        # We use ROW_NUMBER() to ensure if a bill_no + line_no appears twice, we only keep the newest one
        con.execute("""
            CREATE OR REPLACE TABLE sales_fact AS 
            SELECT * EXCLUDE (rn) FROM (
                SELECT *, ROW_NUMBER() OVER (PARTITION BY bill_no, line_no ORDER BY timestamp DESC) as rn
                FROM ({source_query})
            ) 
            WHERE rn = 1;
        """.format(source_query=' UNION ALL '.join(source_queries)))

        # 3. Calculate row count and checksum to prove idempotency
        result = con.execute("""
            SELECT 
                COUNT(*) as row_count,
                SUM(quantity) as check_sum
            FROM sales_fact;
        """).fetchone()

        print(f"Run {run_number} Complete | Row Count: {result[0]} | Checksum (Total Qty): {result[1]}")

if __name__ == "__main__":
    # Run the exact same load process three times in a row
    print("Testing Idempotency...")
    run_load(1)
    run_load(2)
    run_load(3)