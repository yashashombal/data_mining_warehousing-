import duckdb

def run_monthly_report(target_month_name, start_date, end_date):
    with duckdb.connect('annapurna.duckdb', read_only=True) as con:
        # Attach Postgres to access price revisions
        con.execute("""
            INSTALL postgres;
            LOAD postgres;
            ATTACH 'dbname=annapurna user=admin password=password host=localhost port=5432' AS pg (TYPE POSTGRES);
        """)
        
        # Execute query using historical price revisions for the specified date window
        query = f"""
            SELECT 
                '{target_month_name}' AS reporting_period,
                SUM(f.quantity * pr.selling_price) AS total_historical_revenue
            FROM fact_sales f
            JOIN pg.price_revisions pr 
                ON f.product_sk = pr.product_sk
                -- Join strictly against the price that was active on the business date of the sale
                AND f.business_date >= pr.effective_from 
                AND (f.business_date < pr.effective_to OR pr.effective_to IS NULL)
            WHERE f.business_date >= '{start_date}' AND f.business_date <= '{end_date}'
                AND f.line_type = 'SALE';
        """
        
        result = con.execute(query.strip()).fetchone()
        print(f"Report for {result[0]}: Total Revenue = {result[1]:,.2f}")

if __name__ == "__main__":
    print("Demonstrating Point-in-Time Historical Pricing (Same Query, Different Periods):")
    # Run 1: March 2024 pricing
    run_monthly_report("March 2024", "2024-03-01", "2024-03-31")
    
    # Run 2: October 2024 pricing (demonstrating the exact same query logic for a different month)
    run_monthly_report("October 2024", "2024-10-01", "2024-10-31")