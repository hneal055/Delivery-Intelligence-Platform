import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/delivery_db"

async def main():
    engine = create_async_engine(DATABASE_URL)

    async with engine.connect() as conn:
        result = await conn.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )

        print("Tables found:")
        for row in result:
            print(row[0])

    await engine.dispose()

asyncio.run(main())