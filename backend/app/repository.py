import asyncio
import json

from redis.exceptions import RedisError

from .config import env


class GraphRepository:
    """FalkorDB access boundary; uses a process-local store when no connection is configured."""

    def __init__(self) -> None:
        self.graph = None
        self.error = None
        try:
            from falkordb import FalkorDB

            url = env("FALKORDB_URL")
            if url and "localhost" not in url:
                self.db = FalkorDB(url=url, socket_timeout=3, socket_connect_timeout=3)
            else:
                self.db = FalkorDB(
                    host=env("FALKORDB_HOST") or "localhost",
                    port=int(env("FALKORDB_PORT") or "6379"),
                    password=env("FALKORDB_PASSWORD") or None,
                    username=env("FALKORDB_USERNAME") or "default",
                    socket_timeout=3,
                    socket_connect_timeout=3,
                )
            self.graph = self.db.select_graph(env("FALKORDB_GRAPH", "freshcheck"))
        except (ImportError, RedisError, ValueError, TypeError) as exc:
            self.error = str(exc)
        self.runs: dict[str, dict] = {}
        self.claims: list[dict] = []

    async def query(self, cypher: str, params: dict | None = None):
        if not self.graph:
            return None
        return await asyncio.to_thread(self.graph.query, cypher, params or {})

    async def health(self) -> bool:
        if not self.graph:
            return False
        try:
            await self.query("RETURN 1")
            return True
        except (RedisError, AttributeError):
            return False

    async def init(self):
        for query in (
            "CREATE INDEX FOR (e:Entity) ON (e.name)",
            "CREATE INDEX FOR (c:Claim) ON (c.id)",
        ):
            try:
                await self.query(query)
            except RedisError as exc:
                self.error = str(exc)

    async def save_run(self, run: dict):
        self.runs[run["id"]] = run

    async def save_claim(self, claim: dict, finding: dict, verified_at: str):
        self.claims.append({**claim, "finding": finding, "verified_at": verified_at})
        if not self.graph:
            return
        params = {
            "entity": claim["entity"],
            "attribute": claim["attribute"],
            "id": claim["id"],
            "text": claim["text"],
            "value": claim["claimed_value"],
            "claim_type": claim["claim_type"],
            "volatility": claim["volatility"],
            "valid_from": finding.get("value_valid_from") or verified_at,
            "verified_at": verified_at,
            "verdict": finding["verdict"],
            "score": finding.get("score"),
            "label": finding["label"],
            "evidence": json.dumps([e for e in finding.get("evidence", [])]),
        }
        q = """MERGE (e:Entity {name:$entity})
OPTIONAL MATCH (e)-[:HAS_CLAIM]->(old:Claim)
WHERE old.attribute=$attribute AND old.value<>$value AND old.valid_to IS NULL
FOREACH (_ IN CASE WHEN old IS NULL THEN [] ELSE [1] END | SET old.valid_to=$valid_from)
WITH e,old
MERGE (c:Claim {id:$id})
SET c.text=$text,c.attribute=$attribute,c.value=$value,c.claim_type=$claim_type,
c.volatility=$volatility,c.valid_from=$valid_from,c.valid_to=null,c.recorded_at=$verified_at
MERGE (e)-[:HAS_CLAIM]->(c)
CREATE (v:Verification {id:$id+'-'+$verified_at, verdict:$verdict,
score:$score,label:$label,verified_at:$verified_at})
CREATE (c)-[:VERIFIED_BY {at:$verified_at}]->(v)
FOREACH (_ IN CASE WHEN old IS NULL THEN [] ELSE [1] END |
 CREATE (old)-[:SUPERSEDED_BY {detected_at:$verified_at}]->(c))"""
        await self.query(q, params)
        for evidence in finding.get("evidence", []):
            eparams = {
                "url": evidence.get("url", ""),
                "title": evidence.get("title", ""),
                "quote": evidence.get("quote", ""),
                "source_type": evidence.get("source_type", "OTHER"),
                "published_at": evidence.get("published_date"),
                "fetched_at": verified_at,
                "verification_id": claim["id"] + "-" + verified_at,
            }
            await self.query(
                """MATCH (v:Verification {id:$verification_id})
MERGE (e:Evidence {url:$url}) SET e.title=$title,e.quote=$quote,e.source_type=$source_type,
e.published_at=$published_at,e.fetched_at=$fetched_at MERGE (v)-[:SUPPORTED_BY]->(e)""",
                eparams,
            )

    def history(self, entity: str, attribute: str, valid_at: str | None, known_at: str | None):
        items = [
            c
            for c in self.claims
            if c["entity"].lower() == entity.lower() and c["attribute"].lower() == attribute.lower()
        ]
        if known_at:
            items = [c for c in items if c["verified_at"] <= known_at]
        if valid_at:
            items = [
                c for c in items if str(c.get("claimed_as_of") or c["verified_at"]) <= valid_at
            ]
        return items

    async def query_history(
        self, entity: str, attribute: str, valid_at: str | None, known_at: str | None
    ):
        if not self.graph:
            return self.history(entity, attribute, valid_at, known_at)
        result = await self.query(
            """MATCH (e:Entity {name:$entity})-[:HAS_CLAIM]->(c:Claim)
WHERE c.attribute=$attribute AND ($known_at IS NULL OR c.recorded_at <= $known_at)
AND ($valid_at IS NULL OR (c.valid_from <= $valid_at AND (c.valid_to IS NULL OR c.valid_to > $valid_at)))
OPTIONAL MATCH (c)-[:VERIFIED_BY]->(v:Verification)
WHERE $known_at IS NULL OR v.verified_at <= $known_at
RETURN c.id,c.text,c.attribute,c.value,c.valid_from,c.valid_to,c.recorded_at,
v.verdict,v.score,v.label,v.verified_at ORDER BY c.valid_from""",
            {"entity": entity, "attribute": attribute, "valid_at": valid_at, "known_at": known_at},
        )
        keys = [
            "id",
            "text",
            "attribute",
            "claimed_value",
            "valid_from",
            "valid_to",
            "recorded_at",
            "verdict",
            "score",
            "label",
            "verified_at",
        ]
        return [dict(zip(keys, row)) for row in result.result_set]

    def graph_data(self, entity: str | None = None):
        claims = [c for c in self.claims if entity is None or c["entity"].lower() == entity.lower()]
        nodes, edges = [], []
        for c in claims:
            enode, cnode = "e:" + c["entity"], "c:" + c["id"]
            if not any(n["id"] == enode for n in nodes):
                nodes.append({"id": enode, "label": c["entity"], "type": "Entity"})
            nodes.append({"id": cnode, "label": c["claimed_value"], "type": "Claim", "claim": c})
            edges.append({"source": enode, "target": cnode, "label": "HAS_CLAIM"})
        return {"nodes": nodes, "edges": edges}

    async def query_graph_data(self, entity: str | None = None):
        if not self.graph:
            return self.graph_data(entity)
        result = await self.query(
            """MATCH (e:Entity)-[:HAS_CLAIM]->(c:Claim)
WHERE $entity IS NULL OR toLower(e.name)=toLower($entity)
OPTIONAL MATCH (c)-[:VERIFIED_BY]->(:Verification)-[:SUPPORTED_BY]->(ev:Evidence)
RETURN e.name,c.id,c.text,c.value,c.attribute,c.valid_from,c.valid_to,collect(DISTINCT ev.url)""",
            {"entity": entity},
        )
        nodes, edges = [], []
        for name, claim_id, text, value, attribute, valid_from, valid_to, urls in result.result_set:
            eid, cid = "e:" + name, "c:" + claim_id
            if not any(node["id"] == eid for node in nodes):
                nodes.append({"id": eid, "label": name, "type": "Entity"})
            nodes.append(
                {
                    "id": cid,
                    "label": value,
                    "type": "Claim",
                    "claim": {
                        "text": text,
                        "attribute": attribute,
                        "valid_from": valid_from,
                        "valid_to": valid_to,
                    },
                }
            )
            edges.append({"source": eid, "target": cid, "label": "HAS_CLAIM"})
            for url in urls or []:
                if url:
                    vid = "v:" + url
                    if not any(node["id"] == vid for node in nodes):
                        nodes.append({"id": vid, "label": url, "type": "Evidence"})
                    edges.append({"source": cid, "target": vid, "label": "SUPPORTED_BY"})
        return {"nodes": nodes, "edges": edges}
