"""Test all analysis templates"""
import httpx
base = "http://localhost:8000"
t = httpx.post(f"{base}/api/auth/login", json={"username": "admin", "password": "admin123"})
h = {"Authorization": f"Bearer {t.json()['token']}"}

tests = [
    ("trend", {"metric": "order_amount", "granularity": "month", "start_date": 20250101, "end_date": 20250331}),
    ("compare", {"metric": "order_amount", "dimension": "region_name",
     "dim_table": "dim_region", "dim_key": "region_id",
     "dim_name_field": "region_name", "start_date": 20250101, "end_date": 20250331}),
    ("topn", {"metric": "order_amount", "dimension": "category",
     "dim_table": "dim_product", "dim_key": "product_id",
     "dim_name_field": "category", "top_n": 5,
     "start_date": 20250101, "end_date": 20250331}),
    ("distribution", {"metric": "order_amount", "dimension": "region_name",
     "dim_table": "dim_region", "dim_key": "region_id",
     "dim_name_field": "region_name", "start_date": 20250101, "end_date": 20250331}),
]
for tid, params in tests:
    r = httpx.post(f"{base}/api/reports/analyze", headers=h, json={"template_id": tid, "params": params})
    d = r.json()
    has_err = any(k.endswith("_error") for k in d["results"])
    has_chart = d.get("chart_data") is not None
    main_rows = d["results"].get("main", [])
    print(f"[{tid:15s}] status={r.status_code} err={has_err} chart={has_chart} main_rows={len(main_rows)}")
