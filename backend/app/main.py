import asyncio
import json

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import pipeline
from .config import BIFROST_URL, env
from .models import CheckRequest
from .repository import GraphRepository

app = FastAPI(
    title="FreshCheck",
    version="0.1.0",
    description="Detect and review time-sensitive claims in generated text",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
repo = GraphRepository()


@app.on_event("startup")
async def startup():
    await repo.init()


@app.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            bifrost = (await client.get(BIFROST_URL + "/health")).is_success
    except httpx.HTTPError:
        bifrost = False
    return {
        "api": True,
        "falkordb": await repo.health(),
        "bifrost": bifrost,
        "tavily_configured": bool(env("TAVILY_API_KEY")),
        "groq_configured": bool(env("GROQ_API_KEY")),
    }


@app.post("/api/check")
async def check(body: CheckRequest, outage: bool = False):
    async def events():
        queue: asyncio.Queue = asyncio.Queue()

        async def progress(stage, data):
            await queue.put((stage, data))

        task = asyncio.create_task(
            pipeline.run_check(body.text, repo, body.force, outage, progress)
        )
        while not task.done() or not queue.empty():
            try:
                stage, data = await asyncio.wait_for(queue.get(), timeout=0.5)
                yield f"event: {stage}\ndata: {json.dumps(data)}\n\n"
            except TimeoutError:
                if task.done():
                    break
        try:
            result = task.result()
            yield "event: result\ndata: " + json.dumps(result, default=str) + "\n\n"
        except (httpx.HTTPError, RuntimeError, ValueError, TypeError) as exc:
            yield "event: error\ndata: " + json.dumps({"error": str(exc)}) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str):
    return repo.runs.get(run_id, {"error": "run not found"})


@app.get("/api/claims/history")
async def history(
    entity: str, attribute: str, valid_at: str | None = None, known_at: str | None = None
):
    return {"items": await repo.query_history(entity, attribute, valid_at, known_at)}


@app.get("/api/graph")
async def graph(entity: str | None = None):
    return await repo.query_graph_data(entity)


@app.get("/api/stats")
async def get_stats():
    lat = sorted(pipeline.stats["latencies"])
    p = lambda n: lat[min(int((len(lat) - 1) * n), len(lat) - 1)] if lat else 0
    return {
        **pipeline.stats,
        "fallback_events": __import__("app.llm", fromlist=["fallback_events"]).fallback_events,
        "p50_latency": p(0.5),
        "p95_latency": p(0.95),
        "cache_hit_rate": pipeline.stats["cache_hits"]
        / max(1, len(repo.runs) + pipeline.stats["cache_hits"]),
        "credits_saved": pipeline.stats["saved_tavily"],
    }


@app.post("/api/middleware/wrap")
async def wrap(body: dict):
    answer = str(body.get("answer", ""))[:8000]
    result = await pipeline.run_check(answer, repo)
    return {"answer": answer, "corrected_answer": result["corrected"], "claims": result["claims"]}
