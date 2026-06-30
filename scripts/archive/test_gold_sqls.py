"""Test if gold SQLs can execute on the actual database."""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

GOLD_SQLS = [
    ("Q1", "SELECT title FROM albums ORDER BY title"),
    ("Q2", "SELECT address FROM employees WHERE first_name = 'Nancy' AND last_name = 'Edwards'"),
    ("Q3", "SELECT T2.name FROM genres AS T1 JOIN tracks AS T2 ON T1.id = T2.genre_id WHERE T1.name = 'Rock'"),
    ("Q9", "SELECT country FROM customers WHERE first_name = 'Roberto' AND last_name = 'Almeida'"),
]

DB_URL = "mysql+asyncmy://didilili:dili123@localhost:3307/dw"

async def test_gold_sqls():
    engine = create_async_engine(DB_URL)
    async with AsyncSession(engine) as session:
        for label, sql in GOLD_SQLS:
            try:
                r = await session.execute(text(sql))
                rows = r.fetchall()
                print(f"{label}: OK ({len(rows)} rows)")
                if rows:
                    print(f"  First row: {rows[0]}")
            except Exception as e:
                print(f"{label}: FAIL - {e}")
    await engine.dispose()

asyncio.run(test_gold_sqls())
