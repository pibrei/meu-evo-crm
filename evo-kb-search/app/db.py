import json

from psycopg_pool import AsyncConnectionPool

from .config import settings

_pool: AsyncConnectionPool | None = None


async def init_pool() -> None:
    global _pool
    _pool = AsyncConnectionPool(conninfo=settings.dsn, min_size=1, max_size=5, open=False)
    await _pool.open()
    await ensure_schema()


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()


def _vec_literal(vec: list[float]) -> str:
    # pgvector accepts a textual '[1,2,3]' literal cast to ::vector
    return "[" + ",".join(f"{x:.8f}" for x in vec) + "]"


async def ensure_schema() -> None:
    async with _pool.connection() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS kb_chunks (
                id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                source     text,
                content    text NOT NULL,
                metadata   jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                embedding  vector({settings.embed_dim}) NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        await conn.execute("CREATE INDEX IF NOT EXISTS kb_chunks_source_idx ON kb_chunks (source)")
        try:
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS kb_chunks_embedding_idx "
                "ON kb_chunks USING hnsw (embedding vector_cosine_ops)"
            )
        except Exception:
            # HNSW needs pgvector >= 0.5. Search still works without an index
            # (just slower), so a missing index must not break startup.
            pass


async def delete_source(source: str) -> None:
    async with _pool.connection() as conn:
        await conn.execute("DELETE FROM kb_chunks WHERE source = %s", (source,))


async def insert_chunks(rows: list[tuple[str, str, dict, list[float]]]) -> None:
    async with _pool.connection() as conn:
        async with conn.cursor() as cur:
            for source, content, metadata, emb in rows:
                await cur.execute(
                    "INSERT INTO kb_chunks (source, content, metadata, embedding) "
                    "VALUES (%s, %s, %s::jsonb, %s::vector)",
                    (source, content, json.dumps(metadata), _vec_literal(emb)),
                )


async def search(query_vec: list[float], top_k: int, source: str | None = None) -> list[dict]:
    qv = _vec_literal(query_vec)
    async with _pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                SELECT content, source, metadata, 1 - (embedding <=> %s::vector) AS score
                FROM kb_chunks
                WHERE (%s::text IS NULL OR source = %s)
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (qv, source, source, qv, top_k),
            )
            rows = await cur.fetchall()
    return [
        {"content": content, "source": src, "metadata": meta, "score": float(score)}
        for (content, src, meta, score) in rows
    ]
