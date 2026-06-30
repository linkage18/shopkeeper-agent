"""Test SQL normalization approach."""
import re


def normalize_sql(sql: str) -> str:
    """Normalize SQL for comparison."""
    s = sql.strip()
    # Remove trailing semicolons
    s = s.rstrip(";")
    # Remove schema prefix like `dw.`
    s = re.sub(r'`?\w+`?\.', '', s)
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    # Uppercase keywords (simple approach)
    return s.upper()


# Test
gen = "SELECT title AS 标题 FROM albums ORDER BY title ASC"
gold = "SELECT title FROM albums ORDER BY title;"

print(f"Gold norm:      {normalize_sql(gold)}")
print(f"Gen norm:       {normalize_sql(gen)}")
print(f"Match:          {normalize_sql(gen) == normalize_sql(gold)}")

# Also remove AS aliases for comparison
def normalize_sql_strict(sql: str) -> str:
    """Normalize SQL for strict comparison - remove aliases."""
    s = sql.strip().rstrip(";")
    # Remove AS aliases (simple version - removes "AS something" after column names)
    s = re.sub(r'\bAS\s+\w+', '', s)
    # Remove schema prefix
    s = re.sub(r'`?\w+`?\.', '', s)
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s.upper()

print(f"\nWith alias removal:")
print(f"Gold norm:      {normalize_sql_strict(gold)}")
print(f"Gen norm:       {normalize_sql_strict(gen)}")
print(f"Match:          {normalize_sql_strict(gen) == normalize_sql_strict(gold)}")
