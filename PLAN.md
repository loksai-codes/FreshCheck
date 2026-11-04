# FreshCheck build plan

1. Infra and health: FastAPI, React/Vite shell, Docker Compose, Bifrost, remote FalkorDB config.
2. Claim extraction: typed atomic claims, model call through Bifrost, deterministic offline fallback.
3. Verification and scoring: Tavily search/extract, bounded concurrency, evidence quote validation, deterministic scoring.
4. FalkorDB: repository boundary, bi-temporal history, TTL skipping, seeded demo data.
5. Rewriter and API: SSE progress, run persistence, history/graph/stats, middleware wrapper, budget handling.
6. Frontend: checker, claim details/citations, corrected text, timeline graph.
7. Ops: costs/tokens/cache/Tavily/fallback metrics and provider outage simulation.
8. Evals/docs: labeled dataset, scripts, README, tests, compose smoke guidance.

Notes from current docs: Groq retired `llama-3.1-8b-instant` and `llama-3.3-70b-versatile` on 2026-08-16. Defaults use current recommended successors (`openai/gpt-oss-20b` and `openai/gpt-oss-120b`) but remain configurable. FalkorDB is configured as an external hosted service; no local database container is required.
