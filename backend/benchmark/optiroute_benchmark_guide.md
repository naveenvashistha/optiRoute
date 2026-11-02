# OptiRoute Benchmark & Evaluation Guide

This guide provides step-by-step instructions for running, verifying, and analyzing the OptiRoute intelligent gateway benchmark suites (including the 10-query sanity check, the 15-query viva presentation set, and the full 100-query benchmark).

---

## 🏗️ Architecture & Evaluation Overview

OptiRoute is an intelligent LLM gateway that optimizes routing, enforces privacy intent filters, and slashes latency and cost using a high-performance RedisVL semantic cache (powered by BGE-small embeddings and HNSW vector indices).

The benchmark suite evaluates four core behaviors:
1. **Cold-Start Cache Population:** Seeding initial responses into the vector cache.
2. **Exact & Semantic Cache Hits:** Verifying sub-100ms response times for repeated or paraphrased queries.
3. **Semantic Boundary Enforcement (Near-Misses):** Ensuring slight conceptual changes correctly bypass the cache.
4. **Router Judge & Intent Filtering:** Escalating complex architectural queries to Cloud LLMs while keeping private/contextual queries local.

---

## ⚙️ Prerequisites & Setup

Ensure you have Docker, Docker Compose, and Python 3.10+ installed on your machine.

### 1. Start the Backend Infrastructure
Navigate to your backend directory and bring up the containerized services (FastAPI gateway, RedisVL vector database, and frontend):

```bash
docker compose down
docker compose up -d
```

Verify that all containers are healthy and running:
```bash
docker ps
```

---

## Erasing the cache (if required) - run_benchmark has automatic cache clean
docker compose exec -T redis sh -c "redis-cli --scan --pattern 'cache:*' | xargs -r redis-cli del"
docker compose exec -T redis redis-cli FT._LIST
docker compose exec -T redis redis-cli FT.INFO query_cache_idx | Select-String -Context 0,1 "num_docs"

## 🧪 Running the Benchmark Suites

OptiRoute includes multiple evaluation scripts depending on what you want to demonstrate:

### Option A: The 10-Query Sanity Check (`test_10.py`)
Use this for a quick, end-to-end sanity verification of all core routing and caching behaviors.

```bash
python test_10.py
```
* **What it does:** Executes 10 targeted test cases sequentially, verifying cold starts, exact/semantic cache hits, cloud escalation, and intent bypasses, printing a summary pass/fail report.

### Option B: The 15-Query Viva Presentation Set (`run_benchmark.py 15`)
Use this when presenting your project to a professor or evaluator. It runs a curated 15-query set designed to showcase seeds, semantic paraphrases, near-miss negative controls, intent filters, and router escalation.

```bash
python run_benchmark.py 15
```
* **What it does:** Streams the viva dataset against the gateway, records raw telemetry, and saves outputs to `results_15/raw_telemetry.jsonl`.

### Option C: The Full 100-Query Benchmark (`run_benchmark.py`)
Use this for full-scale load and performance evaluation.

```bash
python run_benchmark.py 100
```
* **What it does:** Executes 100 benchmark queries, logging comprehensive metrics to `results_100/raw_telemetry.jsonl`.

---

## 📊 Analyzing and Visualizing Results

Once a benchmark run completes, you can generate comprehensive statistical summaries, confidence intervals, and visualization charts using the analysis script.

To analyze the viva set (`results_15/`):
```bash
python analyze.py 15
```

To analyze the full 100-query run (`results_100/`):
```bash
python analyze.py 100
```

### Generated Artifacts:
* **`summary.json`**: Contains structured metrics for intent accuracy, cache hit rates, router judge accuracy, latency percentiles (p50/p95/mean), and cost savings.
* **`benchmark_charts.png`**: Visualizes the traffic split across routes and cost reductions compared to a 100% cloud baseline.

---

## 🔬 Measuring Gateway Overhead (`overhead_benchmark.py`)
To isolate and measure the gateway's internal decision time (embedding generation, Redis session lookup, intent classification, and DistilBERT difficulty judging) *excluding* LLM generation time:

```bash
python overhead_benchmark.py
```
* **Target:** Verifies that decision overhead remains well below the $100\text{ ms}$ target for cache-hit and cache-miss paths.