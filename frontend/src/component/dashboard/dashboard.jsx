// src/components/dashboard/Dashboard.jsx
import MetricCard from "./metricCard";
import TrafficFunnel from "./trafficFunnel";
import { useTelemetry } from "../../context/metrics";
import { formatCurrency, formatNumber, formatPercentage } from "../../utils/formatter";

export default function Dashboard() {
  const { stats } = useTelemetry();

  const avgLatency =
    stats.totalRequests > 0
      ? Math.round(stats.totalLatencyMs / stats.totalRequests)
      : 0;

  const bypassRate =
    stats.totalRequests > 0
      ? stats.bypassIntentCount / stats.totalRequests
      : 0;

  return (
    <div className="w-full max-w-xl space-y-4 p-4">
      {/* 2x2 Metrics Grid */}
      <div className="grid grid-cols-2 gap-4">
        <MetricCard
          title="Est. Cost Saved"
          value={formatCurrency(stats.costSavedUsd)}
          subtitle="vs. 100% Cloud API"
          valueColor="text-emerald-400"
        />

        <MetricCard
          title="Tokens Offloaded"
          value={formatNumber(stats.tokensOffloaded)}
          subtitle="Via Cache & Local SLM"
          valueColor="text-purple-400"
        />

        <MetricCard
          title="Avg Response Time"
          value={`${avgLatency} ms`}
          subtitle="Blended across all routes"
          valueColor="text-sky-400"
        />

        <MetricCard
          title="Bypass Intent Rate"
          value={formatPercentage(bypassRate)}
          subtitle="MLP Classifier output"
          valueColor="text-amber-400"
        />
      </div>

      {/* Traffic Distribution Funnel */}
      <TrafficFunnel
        totalReqs={stats.totalRequests}
        hits={stats.routeCounts.hits}
        local={stats.routeCounts.local}
        cloud={stats.routeCounts.cloud}
      />
    </div>
  );
}