from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from . import db, embeddings
from .chunking import chunk_text
from .config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pool()
    yield
    await db.close_pool()


app = FastAPI(title="Evo KB Search", version="1.0.0", lifespan=lifespan)


async def require_key(x_api_key: str | None = Header(default=None)) -> None:
    if settings.kb_api_key and x_api_key != settings.kb_api_key:
        raise HTTPException(status_code=401, detail="invalid api key")


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    source: str | None = None


class Document(BaseModel):
    content: str
    source: str
    metadata: dict = Field(default_factory=dict)


class IngestRequest(BaseModel):
    documents: list[Document]
    replace: bool = True


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/search", dependencies=[Depends(require_key)])
async def search(req: SearchRequest):
    if not req.query.strip():
        return {"results": []}
    qvec = await embeddings.embed_query(req.query)
    results = await db.search(qvec, req.top_k, req.source)
    return {"results": results}


@app.post("/ingest", dependencies=[Depends(require_key)])
async def ingest(req: IngestRequest):
    sources = {d.source for d in req.documents}
    if req.replace:
        for s in sources:
            await db.delete_source(s)

    total = 0
    for doc in req.documents:
        chunks = chunk_text(doc.content, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            continue
        vecs = await embeddings.embed_documents(chunks)
        rows = [(doc.source, ch, doc.metadata, v) for ch, v in zip(chunks, vecs)]
        await db.insert_chunks(rows)
        total += len(rows)

    return {"ingested_chunks": total, "sources": sorted(sources)}
