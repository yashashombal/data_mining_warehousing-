import duckdb
from pathlib import Path

with duckdb.connect('annapurna.duckdb') as con:
    # 1. Attach PostgreSQL 
    con.execute("""
        INSTALL postgres;
        LOAD postgres;
        ATTACH 'dbname=annapurna user=admin password=password host=localhost port=5432' AS pg (TYPE POSTGRES);
    """)

    # 2. Configure S3/MinIO secrets for DuckDB
    con.execute("""
        INSTALL httpfs;
        LOAD httpfs;
        SET threads = 1;
        SET httpfs_connection_caching = false;
        DROP SECRET IF EXISTS minio_secret;
        CREATE SECRET minio_secret (
            TYPE S3,
            KEY_ID 'admin',
            SECRET 'password',
            REGION 'us-east-1',
            ENDPOINT '127.0.0.1:9000',
            URL_STYLE 'path',
            USE_SSL false
        );
    """)

    print("Executing Federated Query across MinIO and PostgreSQL...")

    local_partitioned_sales = Path(__file__).resolve().parent / 'partitioned_sales'
    csv_files = [
        's3://sales-data/partitioned_sales/' + path.relative_to(local_partitioned_sales).as_posix()
        for path in local_partitioned_sales.rglob('*.csv')
    ]
    if not csv_files:
        raise FileNotFoundError(f'No CSV files found in {local_partitioned_sales}')
    csv_file_list = ', '.join("'" + path.replace("'", "''") + "'" for path in csv_files)
    local_file_list = ', '.join(
        "'" + path.as_posix().replace("'", "''") + "'"
        for path in local_partitioned_sales.rglob('*.csv')
    )
    
    # 3. We run EXPLAIN ANALYZE to inspect the physical execution plan
    # This query joins the S3 CSV sales files with PostgreSQL categories
    s3_source = f"read_csv_auto([{csv_file_list}], union_by_name = true, all_varchar = true)"
    local_source = f"read_csv_auto([{local_file_list}], union_by_name = true, all_varchar = true)"
    query = f"""
        EXPLAIN ANALYZE
        SELECT 
            c.category_name,
            SUM(TRY_CAST(COALESCE(f.qty, f.quantity) AS DOUBLE) *
                TRY_CAST(COALESCE(f.unit_price, f.rate) AS DOUBLE)) AS total_revenue
        FROM {s3_source} f
        JOIN pg.products p ON f.product_code = p.product_code
        JOIN pg.product_categories c ON p.category_id = c.category_id
        GROUP BY c.category_name;
    """
    
    try:
        plan = con.execute(query).fetchall()
    except duckdb.IOException:
        print("MinIO read failed; retrying the same federated query from the local partition mirror...")
        plan = con.execute(query.replace(s3_source, local_source)).fetchall()
    for row in plan:
        print(row[1] if len(row) > 1 else row[0])