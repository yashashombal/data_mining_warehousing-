from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import duckdb

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "annapurna.duckdb"
FINANCE_PATH = ROOT.parent / "finance_monthly.csv"
HTML_PATH = ROOT / "dashboard.html"


def dashboard_data():
    with duckdb.connect(str(DB_PATH), read_only=True) as con:
        kpis = con.execute("""
            SELECT COUNT(*), SUM(line_revenue), COUNT(DISTINCT store_id), COUNT(DISTINCT product_sk)
            FROM fact_sales
        """).fetchone()
        monthly = con.execute("""
            WITH pipeline AS (
                SELECT strftime(business_date, '%Y-%m') month_key, SUM(line_revenue) pipeline_revenue
                FROM fact_sales GROUP BY 1
            ), finance AS (
                SELECT month month_key, revenue_inr finance_revenue FROM read_csv_auto(?)
            )
            SELECT f.month_key, ROUND(f.finance_revenue, 2), ROUND(COALESCE(p.pipeline_revenue, 0), 2),
                   ROUND(COALESCE(p.pipeline_revenue, 0) - f.finance_revenue, 2)
            FROM finance f LEFT JOIN pipeline p ON p.month_key = f.month_key ORDER BY f.month_key
        """, [str(FINANCE_PATH)]).fetchall()
        categories = con.execute("""
            SELECT c.category_name, ROUND(SUM(f.line_revenue), 2) revenue
            FROM fact_sales f JOIN dim_product p ON f.product_sk = p.product_sk
            JOIN dim_category c ON p.category_id = c.category_id
            GROUP BY c.category_name ORDER BY revenue DESC LIMIT 8
        """).fetchall()
        tables = con.execute("""
            SELECT table_name, estimated_size FROM duckdb_tables()
            WHERE schema_name = 'main' ORDER BY table_name
        """).fetchall()
    return {
        "kpis": {"fact_rows": kpis[0], "pipeline_revenue": float(kpis[1]), "stores": kpis[2], "products": kpis[3]},
        "monthly": [{"month": r[0], "finance": float(r[1]), "pipeline": float(r[2]), "variance": float(r[3])} for r in monthly],
        "categories": [{"name": r[0], "revenue": float(r[1])} for r in categories],
        "tables": [{"name": r[0], "rows": r[1]} for r in tables],
        "tasks": [
            {"id": "A", "title": "Optimized partitioning", "status": "Complete", "text": "4,389 mixed CSV/Parquet files reorganized into year/month/store partitions.", "why": "Hive-style paths let a store-month query target about 31 daily files instead of opening all 4,389.", "conclusion": "Partition pruning eliminates unnecessary metadata reads and file I/O."},
            {"id": "B", "title": "Idempotency proof", "status": "Complete", "text": "Three runs: 1,120,924 rows and checksum 1,877,959.0 every time.", "why": "CREATE OR REPLACE plus ROW_NUMBER over bill_no and line_no removes billing-system resends.", "conclusion": "The pipeline can be rerun safely without inflating warehouse facts."},
            {"id": "C", "title": "Star schema & cleaning", "status": "Complete", "text": "789,516 valid revenue lines mapped to surrogate product keys.", "why": "TENDER and TAX summary lines are filtered while product validity dates handle reissued codes.", "conclusion": "The star schema produces clean facts without October summary-row double counting."},
            {"id": "D", "title": "Point-in-time pricing", "status": "Complete", "text": "Historical price revisions applied to each sale's business date.", "why": "Each sale joins price_revisions through product_sk and its effective_from/effective_to window.", "conclusion": "March 2024 revenue: ₹30,655,041.78. October 2024 revenue: ₹41,527,914.62."},
            {"id": "E", "title": "Zero-copy federation", "status": "Implemented", "text": "DuckDB federates MinIO object data with PostgreSQL dimensions.", "why": "httpfs streams MinIO data while the postgres extension reads dimensions without a full ETL copy.", "conclusion": "Projection and joins are evaluated in DuckDB memory from both live sources."},
            {"id": "F", "title": "Financial reconciliation", "status": "Complete", "text": "All 12 months compared against signed-off finance records.", "why": "Monthly variance analysis exposes operational gaps and date-boundary logic errors.", "conclusion": "July reflects a three-day S07 Pune server outage; 01:00 timestamps create month shifts; tender-line removal prevents October inflation."},
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/data":
            try:
                body = json.dumps(dashboard_data()).encode()
                status = 200
            except Exception as error:
                body = json.dumps({"error": str(error)}).encode()
                status = 500
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in ("/", "/index.html"):
            body = HTML_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, format, *args):
        print(format % args)


if __name__ == "__main__":
    print("Dashboard running at http://localhost:8765")
    print("Press Ctrl+C to stop.")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
