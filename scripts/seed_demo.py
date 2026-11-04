import asyncio
from datetime import datetime, timezone
from backend.app.repository import GraphRepository

async def main():
    repo=GraphRepository()
    await repo.save_claim({"id":"seed-groq-price","entity":"Groq","attribute":"API pricing","text":"Groq input token price was $0.27 per million tokens","claimed_value":"$0.27","claim_type":"PRICING","volatility":"HIGH"},{"verdict":"MATCHES","score":90,"label":"CURRENT","evidence":[]},"2025-01-01T00:00:00+00:00")
    print("Seeded prior Groq claim. Connect FALKORDB_URL to persist it in your hosted graph.")

asyncio.run(main())
