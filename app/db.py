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
            await self._ensure_active_conversation(conn, user["id"])
            return user

    async def _ensure_active_conversation(self, conn, user_id: int) -> int:
        result = await conn.execute(
            '''
            SELECT id
            FROM conversations
            WHERE user_id = %s AND is_active = TRUE
            LIMIT 1
            ''',
            (user_id,),
        )
        row = await result.fetchone()
        if row:
            return row["id"]

        result = await conn.execute(
            '''
            INSERT INTO conversations (user_id, is_active)
            VALUES (%s, TRUE)
            RETURNING id
            ''',
            (user_id,),
        )
        row = await result.fetchone()
        return row["id"]

    async def get_active_conversation_id(self, user_id: int) -> int:
        async with self.pool.connection() as conn:
            return await self._ensure_active_conversation(conn, user_id)

    async def new_conversation(self, user_id: int) -> int:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    '''
                    UPDATE conversations
                    SET is_active = FALSE
                    WHERE user_id = %s AND is_active = TRUE
                    ''',
                    (user_id,),
                )
                result = await conn.execute(
                    '''
                    INSERT INTO conversations (user_id, is_active)
                    VALUES (%s, TRUE)
                    RETURNING id
                    ''',
                    (user_id,),
                )
                row = await result.fetchone()
                return row["id"]

    async def get_recent_messages(
        self,
        conversation_id: int,
        limit: int,
    ) -> list[dict]:
        async with self.pool.connection() as conn:
            result = await conn.execute(
                '''
                SELECT role, content
                FROM (
                    SELECT id, role, content, created_at
                    FROM messages
                    WHERE conversation_id = %s
                      AND role IN ('user', 'assistant')
                    ORDER BY created_at DESC, id DESC
                    LIMIT %s
                ) recent
                ORDER BY created_at ASC, id ASC
                ''',
                (conversation_id, limit),
            )
            return list(await result.fetchall())

    async def save_exchange(
        self,
        conversation_id: int,
        user_text: str,
        assistant_text: str,
    ) -> None:
        async with self.pool.connection() as conn:
            async with conn.transaction():
                await conn.execute(
                    '''
                    INSERT INTO messages (conversation_id, role, content)
                    VALUES (%s, 'user', %s)
                    ''',
                    (conversation_id, user_text),
                )
                await conn.execute(
                    '''
                    INSERT INTO messages (conversation_id, role, content)
                    VALUES (%s, 'assistant', %s)
                    ''',
                    (conversation_id, assistant_text),
                )
