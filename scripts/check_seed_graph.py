"""Check the hosted FalkorDB connection and seed one historical demo verification."""

import asyncio
import socket
import sys
from datetime import UTC, datetime
from pathlib import Path

from redis.exceptions import RedisError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.config import env
from backend.app.repository import GraphRepository


async def main() -> None:
    resolved_ip = env("FALKORDB_SEED_IP")
    cloud_host = env("FALKORDB_HOST")
    if resolved_ip and cloud_host:
        system_getaddrinfo = socket.getaddrinfo

        def getaddrinfo(host, port, *args, **kwargs):
            return system_getaddrinfo(
                resolved_ip if host == cloud_host else host, port, *args, **kwargs
            )

        socket.getaddrinfo = getaddrinfo
    repo = GraphRepository()
    if repo.graph is None:
        detail = str(repo.error or "").lower()
        category = (
            "DNS lookup failed"
            if "getaddrinfo" in detail
            else "TLS or server handshake timed out"
            if "timeout" in detail
            else "authentication failed"
            if "auth" in detail or "password" in detail
            else "connection initialization failed"
        )
        print(f"FalkorDB {category}. No data was written.")
        return
    try:
        await repo.query("RETURN 1")
        await repo.init()
    except RedisError as exc:
        print(
            f"FalkorDB connection failed ({type(exc).__name__}). No data was written."
        )
        return
    timestamp = "2025-01-01T00:00:00+00:00"
    await repo.save_claim(
        {
            "id": "seed-groq-price",
            "entity": "Groq",
            "attribute": "API pricing",
            "text": "Prior Groq input token price was $0.27 per million tokens",
            "claimed_value": "$0.27",
            "claim_type": "PRICING",
            "volatility": "HIGH",
        },
        {"verdict": "MATCHES", "score": 90, "label": "CURRENT", "evidence": []},
        timestamp,
    )
    await repo.query(
        "MATCH (c:Claim {id:$id}) SET c.seeded=true",
        {"id": "seed-groq-price"},
    )
    await repo.query("MATCH (c:Claim {id:$id}) RETURN c.id", {"id": "seed-groq-price"})
    print(
        f"Seeded demo history in graph FreshCheck at {datetime.now(UTC).isoformat()}."
    )


if __name__ == "__main__":
    asyncio.run(main())
