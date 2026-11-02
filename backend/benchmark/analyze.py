"""analyze.py - computes all evaluation metrics from results/raw_telemetry.jsonl"""
import os, sys, json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ARG = sys.argv[1] if len(sys.argv) > 1 else "100"      # usage: python analyze.py [100 | 15 | results_folder]
RESULTS_DIR = os.path.join(HERE, ARG if os.path.isdir(os.path.join(HERE, ARG)) else f"results_{ARG}")
RAW_FILE = os.path.join(RESULTS_DIR, "raw_telemetry.jsonl")
SUMMARY_JSON = os.path.join(RESULTS_DIR, "summary.json")
JUDGE_SAID = {"LOCAL_SLM": 0, "CLOUD_FALLBACK": 0, "CLOUD": 1, "SLM_EMERGENCY_FALLBACK": 1}
CACHE_TARGET_MS = 100

def ci(k, n, z=1.96):
    """Wilson 95% confidence interval - shows how much a small sample can really tell us."""
    if not n: return ""
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** .5) / d
    return f"[95% CI {100 * (c - h):.0f}-{100 * (c + h):.0f}%]"

def pct(a, b): return round(a / b * 100, 1) if b else None
def f(x): return "n/a" if x is None or pd.isna(x) else f"{x:.0f} ms"

def analyze():
    if not os.path.exists(RAW_FILE):
        print("Run run_benchmark.py first."); return
    with open(RAW_FILE, encoding="utf-8") as fh:
        df = pd.DataFrame([json.loads(l) for l in fh if l.strip()])
    ok = df[df["error"].isna() & ~df["actual_route"].isin(["ERR", "NO_TELEMETRY"])].copy()
    by_id = ok.set_index("id")
    S = {"queries_total": len(df), "queries_valid": len(ok)}

    print("\n" + "=" * 72 + "\n OPTIROUTE EVALUATION RESULTS\n" + "=" * 72)
    print(f"Valid queries: {len(ok)} / {len(df)}")

    # cold-cache sanity
    stale = ok[(ok["phase"] == "seed") & (ok["actual_route"] == "CACHE")]["id"].tolist()
    if stale:
        print(f"WARNING: seeds {stale} were served from cache -> cache was not empty. Flush Redis and rerun.")

    # 1. intent
    e = ok[ok["actual_intent"].notna() & ok["expected_intent"].notna()]
    tp = int(((e.expected_intent == 1) & (e.actual_intent == 1)).sum())
    fn = int(((e.expected_intent == 1) & (e.actual_intent == 0)).sum())
    tn = int(((e.expected_intent == 0) & (e.actual_intent == 0)).sum())
    fp = int(((e.expected_intent == 0) & (e.actual_intent == 1)).sum())
    S["intent"] = dict(accuracy_pct=pct(tp + tn, len(e)), tp=tp, fn=fn, tn=tn, fp=fp)
    print(f"1. Intent accuracy: {S['intent']['accuracy_pct']}%  (TP {tp}, FN {fn}, TN {tn}, FP {fp}) {ci(tp + tn, len(e))} on {len(e)} labelled queries")
    print("   FN = cacheable query wrongly bypassed (lost savings); FP = private/contextual query wrongly cacheable (risk).")

    # 2. cache
    probes = ok[ok["category"].str.startswith("cache_eval_") & ~ok["category"].str.contains("nearmiss")]
    def possible(r):
        sid = r["depends_on"]
        return sid in by_id.index and by_id.loc[sid, "actual_intent"] == 1 and by_id.loc[sid, "actual_route"] != "CACHE"
    poss = probes[probes.apply(possible, axis=1)]
    hits = int((poss.actual_route == "CACHE").sum())
    S["cache"] = {"hit_rate_pct": pct(hits, len(poss)), "hits": hits, "possible": len(poss), "probes": len(probes)}
    print(f"2. Cache hit rate (probes whose seed was stored): {S['cache']['hit_rate_pct']}% ({hits}/{len(poss)}) {ci(hits, len(poss))} of {len(probes)} probes")
    for cat in sorted(poss.category.unique()):
        c = poss[poss.category == cat]
        print(f"   - {cat.replace('cache_eval_', ''):<11}: {int((c.actual_route == 'CACHE').sum())}/{len(c)}")
    nm = ok[ok["category"].str.contains("nearmiss")]
    fh = int((nm.actual_route == "CACHE").sum())
    S["cache"]["false_hits"] = fh; S["cache"]["near_miss_tests"] = len(nm)
    print(f"   False hits on near-miss queries: {fh}/{len(nm)}  (should be 0) {ci(fh, len(nm))}")
    inc = ok[(ok.actual_route == "CACHE") & (ok.actual_intent == 0)]["id"].tolist()
    if inc: print(f"   INCONSISTENT records (CACHE with intent 0): {inc}")

    # 3. judge
    live = ok[ok.actual_route.isin(JUDGE_SAID) & ok.expected_difficulty.notna()].copy()
    live["said"] = live.actual_route.map(JUDGE_SAID)
    correct = int((live.said == live.expected_difficulty).sum())
    S["judge"] = {"accuracy_pct": pct(correct, len(live)), "correct": correct, "total": len(live)}
    print(f"3. Router judge accuracy: {S['judge']['accuracy_pct']}% ({correct}/{len(live)}) {ci(correct, len(live))}")
    for d, name in ((0, "easy"), (1, "hard")):
        c = live[live.expected_difficulty == d]
        print(f"   - {name:<4}: {int((c.said == d).sum())}/{len(c)}")
    if "borderline" in live.columns:
        for flag, name in ((False, "clear cases"), (True, "borderline")):
            c = live[live["borderline"].fillna(False).astype(bool) == flag]
            if len(c): print(f"   - {name:<11}: {int((c.said == c.expected_difficulty).sum())}/{len(c)}")
    fb = int(live.actual_route.str.contains("FALLBACK").sum())
    S["judge"]["fallback_events"] = fb
    print(f"   Fallback events (provider limits/failures): {fb}")

    # 4. latency
    print("4. Latency by route (gateway-side | time-to-first-token), mean / p50 / p95:")
    S["latency"] = {}
    for route, g in ok.groupby("actual_route"):
        gl, tt = g["gateway_latency_ms"], g["ttft_ms"]
        S["latency"][route] = dict(n=len(g), gw_mean=round(gl.mean(), 1), gw_p50=round(gl.median(), 1),
                                   gw_p95=round(gl.quantile(.95), 1), ttft_mean=round(tt.mean(), 1))
        print(f"   {route:<22} n={len(g):<3} gw {f(gl.mean())} / {f(gl.median())} / {f(gl.quantile(.95))} | ttft {f(tt.mean())}")
    c = S["latency"].get("CACHE")
    if c:
        print(f"   Cache-hit gateway latency {c['gw_mean']:.0f} ms vs target < {CACHE_TARGET_MS} ms: "
              f"{'MET' if c['gw_mean'] < CACHE_TARGET_MS else 'NOT MET'}")

    # 5. cost
    base, act, saved = ok.baseline_cost_usd.sum(), ok.actual_cost_usd.sum(), ok.cost_saved_usd.sum()
    S["cost"] = dict(baseline_usd=round(base, 6), actual_usd=round(act, 6), saved_usd=round(saved, 6),
                     savings_pct=pct(saved, base))
    print(f"5. Cost (baseline = 100% cloud tier at GPT-4o-mini rates): baseline ${base:.5f} | OptiRoute ${act:.5f} | "
          f"saved ${saved:.5f} ({S['cost']['savings_pct']}%)")
    S["routes"] = ok.actual_route.value_counts().to_dict()
    print(f"   Route split: {S['routes']}\n" + "=" * 72)

    with open(SUMMARY_JSON, "w", encoding="utf-8") as fh_:
        json.dump(S, fh_, indent=2, default=lambda o: None if pd.isna(o) else float(o))
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    rc = ok.actual_route.value_counts()
    ax[0].bar(rc.index, rc.values, color="#3B82F6"); ax[0].set_title("Traffic split across routes")
    ax[0].tick_params(axis="x", rotation=20)
    ax[1].bar(["Baseline (100% cloud)", "OptiRoute"], [base, act], color=["#EF4444", "#10B981"])
    ax[1].set_title(f"Cost ({S['cost']['savings_pct']}% saved)")
    plt.tight_layout(); plt.savefig(os.path.join(RESULTS_DIR, "benchmark_charts.png"), dpi=200); plt.close()
    print(f"Saved {SUMMARY_JSON} and benchmark_charts.png")

if __name__ == "__main__":
    analyze()