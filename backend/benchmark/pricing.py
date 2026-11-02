"""
pricing.py - rate card for the cost simulation.
Baseline = every query sent to the SAME cloud tier that OptiRoute uses (GPT-4o-mini rates,
a stand-in for the efficient cloud model). The saving therefore measures only what routing
achieves: queries answered by the cache or the SLM cost $0, queries that reach the cloud
cost the same as in the baseline. (SLM is on a free tier / local: state this in the report.)
"""
CLOUD_TIER_INPUT_PER_M = 0.150
CLOUD_TIER_OUTPUT_PER_M = 0.600

# Baseline uses the same cloud-tier rates, so the comparison isolates the effect of routing.
BASELINE_INPUT_PER_M = CLOUD_TIER_INPUT_PER_M
BASELINE_OUTPUT_PER_M = CLOUD_TIER_OUTPUT_PER_M

ZERO_COST_ROUTES = {"CACHE", "LOCAL_SLM", "SLM_EMERGENCY_FALLBACK"}  # emergency fallback runs on the SLM
CLOUD_ROUTES = {"CLOUD", "CLOUD_FALLBACK"}

def compute_query_cost(input_tokens: int, output_tokens: int, route: str) -> dict:
    baseline = (input_tokens / 1e6) * BASELINE_INPUT_PER_M + (output_tokens / 1e6) * BASELINE_OUTPUT_PER_M
    if route in CLOUD_ROUTES:
        actual = (input_tokens / 1e6) * CLOUD_TIER_INPUT_PER_M + (output_tokens / 1e6) * CLOUD_TIER_OUTPUT_PER_M
    else:
        actual = 0.0
    return {"baseline_cost_usd": baseline, "actual_cost_usd": actual,
            "cost_saved_usd": max(0.0, baseline - actual)}