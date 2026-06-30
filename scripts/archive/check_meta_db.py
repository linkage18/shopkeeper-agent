"""Check meta database contents."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text


async def check():
    engine = create_async_engine(
        "mysql+asyncmy://didilili:dili123@localhost:3307/meta"
    )
    async with AsyncSession(engine) as session:
        r = await session.execute(text("select count(*) from table_info"))
        print(f"table_info rows: {r.scalar()}")
        r = await session.execute(text("select id, name from table_info limit 15"))
        for row in r:
            print(f"  {row}")

        r = await session.execute(text("select count(*) from column_info"))
        print(f"\ncolumn_info rows: {r.scalar()}")

        r = await session.execute(text("select count(*) from metric_info"))
        print(f"metric_info rows: {r.scalar()}")

    await engine.dispose()


asyncio.run(check())
