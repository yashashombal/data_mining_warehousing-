import duckdb

with duckdb.connect('annapurna.duckdb') as con:
    
    # 1. Attach PostgreSQL to read the master dimension tables directly
    con.execute("""
        INSTALL postgres;
        LOAD postgres;
        ATTACH 'dbname=annapurna user=admin password=password host=localhost port=5432' AS pg (TYPE POSTGRES);
    """)

    # 2. Create local Dimension Tables to avoid repeating strings
    print("Creating Dimension Tables...")
    con.execute("""
        CREATE OR REPLACE TABLE dim_store AS SELECT * FROM pg.stores;
        CREATE OR REPLACE TABLE dim_category AS SELECT * FROM pg.product_categories;
        CREATE OR REPLACE TABLE dim_product AS SELECT * FROM pg.products;
    """)

    # 3. Create the Fact Table
    # - We filter out 'TENDER' and 'TAX' to prevent double-counting revenue.
    # - We extract 'day_of_week' and 'month' directly into the table for fast dashboard slicing.
    # - We join on both product_code AND the business date to handle reissued codes correctly.
    print("Creating Fact Table...")
    con.execute("""
        CREATE OR REPLACE TABLE fact_sales AS 
        SELECT 
            s.bill_no,
            s.line_no,
            split_part(s.bill_no, '/', 1) AS store_id,
            p.product_sk,
            s.quantity,
            s.unit_price,
            (s.quantity * s.unit_price) AS line_revenue,
            s.timestamp::DATE AS business_date,
            DAYNAME(s.timestamp::DATE) AS day_of_week,
            MONTHNAME(s.timestamp::DATE) AS sales_month,
            s.line_type
        FROM sales_fact s
        -- Map product code to surrogate key based on when the product was actually valid
        LEFT JOIN pg.products p 
            ON s.product_code = p.product_code 
            AND s.timestamp::DATE >= p.valid_from 
            AND (s.timestamp::DATE <= p.valid_to OR p.valid_to IS NULL)
        -- Keep standard sales and cancellations, but drop tender/tax summary lines
        WHERE s.line_type IN ('SALE', 'VOID', 'RETURN', 'DISCOUNT');
    """)

    # Verify the table creation
    row_count = con.execute("SELECT COUNT(*) FROM fact_sales;").fetchone()[0]
    print(f"Dashboard tables created successfully. Fact table contains {row_count} valid revenue lines.")