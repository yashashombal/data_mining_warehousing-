import duckdb
from pathlib import Path

with duckdb.connect('annapurna.duckdb', read_only=True) as con:
    finance_file = Path(__file__).resolve().parent.parent / 'finance_monthly.csv'
    query = """
        WITH finance AS (
            SELECT month, revenue_inr AS finance_revenue
            FROM read_csv_auto(?)
        ),
        pipeline AS (
            SELECT 
                strftime(business_date, '%Y-%m') AS month,
                SUM(line_revenue) AS pipeline_revenue
            FROM fact_sales
            GROUP BY strftime(business_date, '%Y-%m')
        )
        SELECT 
            f.month,
            f.finance_revenue,
            p.pipeline_revenue,
            (p.pipeline_revenue - f.finance_revenue) AS variance
        FROM finance f
        LEFT JOIN pipeline p ON f.month = p.month
        ORDER BY f.month;
    """
    
    # Print as a clean DataFrame for easy reading
    print("Monthly Revenue Reconciliation (Pipeline vs. Finance):")
    result = con.execute(query, [str(finance_file)])
    print(' | '.join(column[0] for column in result.description))
    for row in result.fetchall():
        print(' | '.join(str(value) for value in row))