import asyncpg

from core.adapters.base_relational import BaseRelationalAdapter


class AsyncPostgresAdapter(BaseRelationalAdapter):
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool = None

    async def connect(self):
        if self.pool is None:
            self.pool = await asyncpg.create_pool(self.dsn)

    async def execute(self, sql: str, params=None, **kwargs):
        await self.connect()
        async with self.pool.acquire() as conn:
            return await conn.fetch(sql, params or [])

    async def close(self):
        if self.pool:
            await self.pool.close()
