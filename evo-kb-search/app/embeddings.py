import httpx

from .config import settings


async def _embed(texts: list[str]) -> list[list[float]]:
    """Call an OpenAI-compatible /embeddings endpoint and return vectors in order."""
    headers = {"Content-Type": "application/json"}
    if settings.embed_api_key:
        headers["Authorization"] = f"Bearer {settings.embed_api_key}"
    payload = {"model": settings.embed_model, "input": texts}

    url = f"{settings.embed_base_url.rstrip('/')}/embeddings"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()["data"]

    # Preserve input order (the API returns an "index" per item).
    return [item["embedding"] for item in sorted(data, key=lambda d: d["index"])]


async def embed_documents(texts: list[str]) -> list[list[float]]:
    return await _embed([settings.doc_prefix + t for t in texts])


async def embed_query(text: str) -> list[float]:
    vecs = await _embed([settings.query_prefix + text])
    return vecs[0]
