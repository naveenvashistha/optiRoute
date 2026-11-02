"""
run_benchmark.py - streams queries sequentially into OptiRoute and logs raw telemetry.
Usage:
    python run_benchmark.py            -> 100-query benchmark  (results_100/)
    python run_benchmark.py 15         -> 15-query viva set    (results_15/)
    python run_benchmark.py <file.jsonl> [results_dir]
Add --keep-cache to skip the automatic cache clearing. Never run FLUSHALL (it deletes the search index).
"""
import os, sys, time, json, uuid, asyncio, subprocess
import httpx
from pricing import compute_query_cost

HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
DATASETS = {"100": "queries_100_benchmark.jsonl", "15": "queries_15_viva.jsonl"}
CHOICE = ARGS[0] if ARGS else "100"
DATASET_FILE = os.path.join(HERE, DATASETS.get(CHOICE, CHOICE))
TAG = CHOICE if CHOICE in DATASETS else os.path.splitext(os.path.basename(CHOICE))[0]
RESULTS_DIR = os.path.join(HERE, ARGS[1] if len(ARGS) > 1 else f"results_{TAG}")
REDIS_CONTAINER = os.getenv("REDIS_CONTAINER", "optiroute-redis-1")
GATEWAY_URL = "http://127.0.0.1:8000/api/ask"
PAUSE_S = 3.0
os.makedirs(RESULTS_DIR, exist_ok=True)
RAW_OUTPUT_FILE = os.path.join(RESULTS_DIR, "raw_telemetry.jsonl")

def est_tokens(text: str) -> int:   # same heuristic as the backend metrics.py (words x 1.33)
    return int(len(text.split()) * 1.33) if text else 0

async def test_single_query(client, rec):
    payload = {"session_id": str(uuid.uuid4()),
               "messages": [{"role": "user", "content": rec["query"]}],
               "edit_index": None}
    t0 = time.perf_counter()
    ttft, telemetry, error, parts = None, {}, None, []
    try:
        async with client.stream("POST", GATEWAY_URL, json=payload, timeout=180.0) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                error = f"HTTP {resp.status_code}: {body.decode('utf-8', 'ignore')[:200]}"
            else:
                async for line in resp.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        ev = json.loads(line[6:])
                    except json.JSONDecodeError:
                        continue
                    if "chunk" in ev:
                        if ttft is None:
                            ttft = (time.perf_counter() - t0) * 1000
                        parts.append(ev["chunk"])
                    elif "telemetry" in ev:
                        telemetry = ev["telemetry"]
                    elif "error" in ev:
                        error = ev["error"]
    except Exception as e:
        error = f"{type(e).__name__}: {e}"

    total_ms = (time.perf_counter() - t0) * 1000
    answer = "".join(parts)
    in_tok, out_tok = max(1, est_tokens(rec["query"])), est_tokens(answer)
    route = telemetry.get("route") or ("ERR" if error else "NO_TELEMETRY")
    costs = compute_query_cost(in_tok, out_tok, route)
    return {
        **rec,
        "actual_route": route,
        "actual_intent": telemetry.get("intent"),
        "gateway_latency_ms": telemetry.get("latency_ms"),
        "client_total_latency_ms": round(total_ms, 2),
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "input_tokens": in_tok, "output_tokens": out_tok,
        **costs, "error": error,
    }

def clear_cache():
    """Delete only the cached answers (cache:*) in the Docker Redis; the search index is kept."""
    cmd = ["docker", "exec", REDIS_CONTAINER, "sh", "-c",
           "redis-cli --scan --pattern 'cache:*' | xargs -r redis-cli del"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            print(f"Cache cleared (cache:* entries deleted, index kept). {r.stdout.strip()}")
        else:
            print(f"WARNING: could not clear cache ({r.stderr.strip()[:120]}). Clear it manually before trusting hit rates.")
    except Exception as e:
        print(f"WARNING: could not clear cache ({type(e).__name__}). Clear it manually before trusting hit rates.")

async def main():
    with open(DATASET_FILE, encoding="utf-8") as f:
        records = [json.loads(l) for l in f if l.strip()]
    print(f"Loaded {len(records)} queries. Target: {GATEWAY_URL}\n")
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get("http://127.0.0.1:8000/api/ready", timeout=5.0)
            if r.status_code != 200:
                print("Backend not ready (is Redis up?)"); return
        except Exception as e:
            print(f"Cannot reach backend: {e}"); return
        if "--keep-cache" not in sys.argv:
            clear_cache()
        with open(RAW_OUTPUT_FILE, "w", encoding="utf-8") as out:
            for i, rec in enumerate(records, 1):
                res = await test_single_query(client, rec)
                out.write(json.dumps(res) + "\n"); out.flush()
                icon = "❌" if res["error"] else "✅"
                print(f"[{i:02d}/{len(records)}] {icon} {res['id']} {res['actual_route']:<22} "
                      f"intent={res['actual_intent']} | {res['client_total_latency_ms']:>8.0f}ms | {rec['query'][:40]}")
                if res["error"]:
                    print(f"        error: {res['error']}")
                await asyncio.sleep(PAUSE_S)
    print(f"\nDone. Raw data: {RAW_OUTPUT_FILE}\nNext: python analyze.py {TAG}")

if __name__ == "__main__":
    asyncio.run(main())