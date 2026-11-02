"""
overhead_benchmark.py - measures the gateway's OWN decision time (no LLM involved).
Runs INSIDE the backend container, using the exact same functions the orchestrator calls.

Stages timed per query:
  state   = sync_session_state + sanitize_and_truncate + update_global_state (Redis session handling)
  intent  = predict_intent   (embedding + MLP)
  cache   = check_cache      (embedding again + RedisVL lookup)
  judge   = evaluate_difficulty (DistilBERT)
Paths reported (the judge now runs only AFTER a cache miss):
  Cache-hit path   : state + intent + cache                    (judge skipped)
  Cache-miss path  : state + intent + cache + judge            (same total as the old "judge first" order)
  Bypassed query   : state + intent + judge                    (cache lookup skipped)
"""
import json, os, time, uuid, statistics as st
from types import SimpleNamespace
from src.services.embedding import get_embedding
from src.services.classifier import predict_intent
from src.services.cache import check_cache
from src.services.router import evaluate_difficulty
from src.services.context_manager import sanitize_and_truncate
from src.core.state import sync_session_state, update_global_state
from src.core.db import redis_client

N = int(os.getenv("N", "20"))
TARGET_MS = 100

with open("/tmp/q.jsonl", encoding="utf-8") as f:
    qs = [json.loads(l)["query"] for l in f if l.strip()]
step = max(1, len(qs) // N)
qs = qs[::step][:N]

def timed(fn, *a):
    t = time.perf_counter(); fn(*a); return (time.perf_counter() - t) * 1000

def state_stage(q):
    sid = str(uuid.uuid4())
    t = time.perf_counter()
    hist = sync_session_state(sid, [SimpleNamespace(role="user", content=q)], None)
    g, _ = sanitize_and_truncate(hist, max_input_tokens=8000)
    update_global_state(sid, g)
    ms = (time.perf_counter() - t) * 1000
    redis_client.delete(f"session:{sid}")
    return ms

# warm-up (model load / first-call cost is excluded)
w = qs[0]
state_stage(w); predict_intent(w); check_cache(w); evaluate_difficulty(w); get_embedding(w)

rows = []
for q in qs:
    rows.append(dict(embed=timed(get_embedding, q), state=state_stage(q),
                     intent=timed(predict_intent, q), cache=timed(check_cache, q),
                     judge=timed(evaluate_difficulty, q)))

def stats(xs):
    xs = sorted(xs)
    return st.mean(xs), st.median(xs), xs[min(len(xs) - 1, int(0.95 * len(xs)))]

print(f"\nGateway decision overhead, {len(qs)} queries (warm, LLM excluded)")
print(f"{'stage':<34}{'mean':>9}{'p50':>9}{'p95':>9}   (ms)")
for k, label in (("embed", "embedding alone (info)"), ("state", "session state (Redis)"),
                 ("intent", "intent check"), ("cache", "cache lookup"), ("judge", "difficulty judge")):
    m, p50, p95 = stats([r[k] for r in rows])
    print(f"{label:<34}{m:>9.1f}{p50:>9.1f}{p95:>9.1f}")

miss = [r["state"] + r["intent"] + r["cache"] + r["judge"] for r in rows]
hit = [r["state"] + r["intent"] + r["cache"] for r in rows]
byp = [r["state"] + r["intent"] + r["judge"] for r in rows]
print("-" * 61)
for name, v in (("Cache-hit path (judge skipped)", hit), ("Cache-miss path (judge runs)", miss), ("Bypassed query (judge runs)", byp)):
    m, p50, p95 = stats(v)
    print(f"{name:<34}{m:>9.1f}{p50:>9.1f}{p95:>9.1f}   target <{TARGET_MS}: {'MET' if m < TARGET_MS else 'NOT MET'}")
print("These are decision times before the language model starts. The cache-miss total equals the old judge-first order.\n")