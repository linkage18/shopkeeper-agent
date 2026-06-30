"""Test improved SQL normalization."""
import re


def normalize_sql(sql: str) -> str:
    """Normalize SQL for string comparison."""
    s = sql.strip().rstrip(";").strip()
    # Only remove explicit schema prefix like dw. or `dw`.
    s = re.sub(r'`?dw`?\.', '', s)
    # But keep table aliases (t.name stays as t.name)
    # Replace double quotes with single quotes in values
    s = re.sub(r'"', "'", s)
    # Strip column aliases (AS xxx)
    s = re.sub(r'\bAS\s+\w+\s*,', ',', s)
    s = re.sub(r'\bAS\s+\w+\s+(FROM|WHERE|JOIN|INNER|LEFT|RIGHT|ON|ORDER|GROUP|LIMIT|HAVING|UNION)', r' \1', s)
    s = re.sub(r'\bAS\s+\w+\s*$', '', s)
    # Remove ASC
    s = re.sub(r'\bASC\b', '', s)
    # Remove redundant commas before FROM/JOIN/WHERE
    s = re.sub(r',\s+FROM', ' FROM', s)
    s = re.sub(r',\s+WHERE', ' WHERE', s)
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s.upper()


test_cases = [
    # (generated, gold, expected_match)
    (
        "SELECT title AS 专辑标题 FROM albums ORDER BY title ASC",
        "SELECT title FROM albums ORDER BY title;",
        True
    ),
    (
        "SELECT address FROM employees WHERE first_name = 'Nancy' AND last_name = 'Edwards'",
        'SELECT address FROM employees WHERE first_name = "Nancy" AND last_name = "Edwards";',
        True
    ),
    (
        "SELECT t.name AS track_name FROM tracks t JOIN genres g ON t.genre_id = g.id WHERE g.name = 'Rock'",
        'SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id WHERE T1.name = "Rock";',
        True
    ),
    (
        "SELECT c.first_name, c.last_name FROM invoices i JOIN customers c ON i.customer_id = c.id ORDER BY i.total ASC LIMIT 10",
        'SELECT T1.first_name ,  T1.last_name FROM customers AS T1 JOIN invoices AS T2 ON T2.customer_id  =  T1.id ORDER BY total ASC LIMIT 10;',
        True
    ),
    (
        "SELECT country FROM customers WHERE first_name = 'Roberto' AND last_name = 'Almeida'",
        'SELECT country FROM customers WHERE first_name = "Roberto" AND last_name = "Almeida";',
        True
    ),
]

for gen, gold, expected in test_cases:
    gn = normalize_sql(gen)
    gdn = normalize_sql(gold)
    match = gn == gdn
    status = "OK" if match == expected else "FAIL"
    print(f"{status}")
    print(f"  gen:  {gn}")
    print(f"  gold: {gdn}")
    print()
