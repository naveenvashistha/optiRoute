"""
test_10.py
Executes the 10-query sanity test against OptiRoute Gateway.
Verifies all 4 evaluation behaviors:
- Cold-start cache population
- Exact & semantic cache hits
- Router judge cloud escalation
- Intent filter cache bypass
"""

import asyncio
import json
import os
import time
import uuid
import httpx

GATEWAY_URL = "http://127.0.0.1:8000/api/ask"
DATA_FILE = "queries_10_sanity.jsonl"

# Track session IDs across dependent test pairs for cache evaluation
SESSION_MAP = {}

async def run_query(client: httpx.AsyncClient, item: dict) -> dict:
    query_text = item.get("query") or item.get("prompt", "")
    item_id = item.get("id")
    
    # Reuse session ID for dependent cache evaluation test pairs
    if item_id == "TEST-03":
        session_id = SESSION_MAP.get("TEST-01", str(uuid.uuid4()))
    elif item_id == "TEST-04":
        session_id = SESSION_MAP.get("TEST-02", str(uuid.uuid4()))
    elif item_id == "TEST-10":
        session_id = SESSION_MAP.get("TEST-09", str(uuid.uuid4()))
    else:
        session_id = str(uuid.uuid4())
        SESSION_MAP[item_id] = session_id

    payload = {
        "session_id": session_id,
        "messages": [{"role": "user", "content": query_text}],
        "edit_index": None,
    }

    t0 = time.perf_counter()
    ttft = None
    telemetry = None
    chunks = []
    error = None

    try:
        async with client.stream(
            "POST", GATEWAY_URL, json=payload, timeout=45.0
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                total_lat = (time.perf_counter() - t0) * 1000
                return {
                    "id": item.get("id", "TEST-??"),
                    "query": query_text,
                    "target_route": item.get("target_route"),
                    "actual_route": f"HTTP_{response.status_code}",
                    "latency_ms": round(total_lat, 2),
                    "ttft_ms": round(total_lat, 2),
                    "intent": None,
                    "test_goal": item.get("test_goal", ""),
                    "error": f"Status {response.status_code}: {body.decode('utf-8', errors='ignore')}",
                }

            async for line in response.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw_str = line[6:].strip()
                if not raw_str:
                    continue

                try:
                    event = json.loads(raw_str)
                    if "chunk" in event:
                        if ttft is None:
                            ttft = (time.perf_counter() - t0) * 1000
                        chunks.append(event["chunk"])
                    elif "telemetry" in event:
                        telemetry = event["telemetry"]
                    elif "error" in event:
                        error = event["error"]
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        error = str(e)

    total_lat = (time.perf_counter() - t0) * 1000
    actual_route = (
        telemetry.get("route", "ERR")
        if telemetry
        else ("ERR" if error else "LOCAL_SLM")
    )

    return {
        "id": item.get("id", "TEST-??"),
        "query": query_text,
        "target_route": item.get("target_route"),
        "actual_route": actual_route,
        "latency_ms": round(total_lat, 2),
        "ttft_ms": round(ttft, 2) if ttft else round(total_lat, 2),
        "intent": telemetry.get("intent") if telemetry else None,
        "test_goal": item.get("test_goal", ""),
        "error": error,
    }


async def main():
    if not os.path.exists(DATA_FILE):
        print(f"❌ Error: {DATA_FILE} not found in current working directory: {os.getcwd()}")
        return

    queries = []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    print("\n" + "=" * 70)
    print(" 🧪 OPTIROUTE 10-QUERY SANITY BENCHMARK")
    print(f" Target: {GATEWAY_URL}")
    print("=" * 70)

    async with httpx.AsyncClient() as client:
        try:
            h = await client.get("http://127.0.0.1:8000/api/ready", timeout=5.0)
            if h.status_code != 200:
                h = await client.get("http://127.0.0.1:8000/api/health", timeout=5.0)
                if h.status_code != 200:
                    print(f"❌ Backend healthcheck returned HTTP {h.status_code}.")
                    return
        except Exception as e:
            print(f"❌ Cannot connect to backend server: {e}")
            print("💡 Ensure Docker Compose is up: docker compose up")
            return

        results = []
        for i, q in enumerate(queries):
            res = await run_query(client, q)
            results.append(res)

            matched = res["actual_route"] == res["target_route"]
            icon = "✅" if matched else "⚠️"
            if res.get("error"):
                icon = "❌"

            print(
                f"[{res['id']}] {icon} Route: {res['actual_route']:<12} | "
                f"Expected: {res['target_route']:<10} | "
                f"Latency: {res['latency_ms']:>6.1f}ms"
            )
            print(f"       Prompt: \"{res['query'][:55]}...\"")
            print(f"       Goal  : {res['test_goal']}")
            if res.get("error"):
                print(f"       ⚠️ Error Details: {res['error']}")
            print()

            # 4-second pause to prevent Groq free-tier rate limits
            await asyncio.sleep(4.0)

    print("=" * 70)
    print(" 📋 SANITY TEST VERIFICATION SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r["actual_route"] == r["target_route"])
    print(f"Route Matches        : {passed} / {len(queries)}")

    cache_items = [r for r in results if r["target_route"] == "CACHE"]
    cache_hits = sum(1 for r in cache_items if r["actual_route"] == "CACHE")
    denom = len(cache_items) if cache_items else 1
    print(f"Cache Hit Accuracy   : {cache_hits} / {denom} ({cache_hits/denom*100:.0f}%)")

    cloud_items = [r for r in results if r["target_route"] == "CLOUD"]
    cloud_hits = sum(1 for r in cloud_items if r["actual_route"] in ["CLOUD", "CLOUD_FALLBACK"])
    denom_c = len(cloud_items) if cloud_items else 1
    print(f"Cloud Router Accuracy: {cloud_hits} / {denom_c} ({cloud_hits/denom_c*100:.0f}%)")

    bypass_items = [r for r in results if r["id"] in ["TEST-07", "TEST-08"]]
    bypasses = sum(1 for r in bypass_items if r["actual_route"] == "LOCAL_SLM")
    denom_b = len(bypass_items) if bypass_items else 1
    print(f"Cache Bypass Accuracy: {bypasses} / {denom_b} ({bypasses/denom_b*100:.0f}%)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())