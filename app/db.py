from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


class Database:
    def __init__(self, database_url: str) -> None:
        self.pool = AsyncConnectionPool(
            conninfo=database_url,
            min_size=1,
            max_size=4,
            open=False,
            kwargs={"row_factory": dict_row},
        )

    async def open(self) -> None:
        await self.pool.open()
        await self.pool.wait()

    async def close(self) -> None:
        await self.pool.close()

    async def init_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")

        async with self.pool.connection() as conn:
            await conn.execute(schema_sql)

    async def ping(self) -> bool:
        async with self.pool.connection() as conn:
            result = await conn.execute("SELECT 1 AS ok")
            row = await result.fetchone()
            return bool(row and row["ok"] == 1)

    async def ensure_user(
        self,
        telegram_id: int,
        first_name: str | None,
        username: str | None,
    ) -> dict:
        async with self.pool.connection() as conn:
            result = await conn.execute(
                '''
                INSERT INTO users (telegram_id, first_name, username)
                VALUES (%s, %s, %s)
                ON CONFLICT (telegram_id)
                DO UPDATE SET
                    first_name = EXCLUDED.first_name,
                    username = EXCLUDED.username,
                    updated_at = NOW()
                RETURNING id, telegram_id, first_name, username
                ''',
                (telegram_id, first_name, username),
            )
            user = await result.fetchone()

            await conn.execute(
                '''
                INSERT INTO conversations (user_id)
                SELECT %s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM conversations
                    WHERE user_id = %s AND is_active = TRUE
                )
                ''',
                (user["id"], user["id"]),
            )

            return user
