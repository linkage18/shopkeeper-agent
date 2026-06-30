"""Test sqlglot-based SQL normalization."""
import sqlglot
import re


def normalize_sql(sql: str) -> str:
    """Use sqlglot to normalize SQL for comparison."""
    try:
        parsed = sqlglot.parse_one(sql)
        # Dialect-aware pretty printing
        return parsed.sql(dialect="mysql", pretty=False)
    except Exception:
        # Fallback basic normalization
        s = sql.strip().rstrip(";")
        s = re.sub(r'`?\w+`?\.', '', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s.upper()


# Test
gen = "SELECT title AS 标题 FROM albums ORDER BY title ASC"
gold = "SELECT title FROM albums ORDER BY title;"

print(f"sqlglot gen:  {normalize_sql(gen)}")
print(f"sqlglot gold: {normalize_sql(gold)}")
print(f"Match: {normalize_sql(gen) == normalize_sql(gold)}")

# More test cases
cases = [
    (gen, gold),
    ("SELECT title FROM albums ORDER BY title", "SELECT title FROM albums ORDER BY title;"),
    ("select title from albums order by title asc", "SELECT title FROM albums ORDER BY title;"),
]

for g, r in cases:
    ng = normalize_sql(g)
    nr = normalize_sql(r)
    print(f"\n  '{g[:50]}'")
    print(f"  -> '{ng}'")
    print(f"  == '{nr}' ? {ng == nr}")
