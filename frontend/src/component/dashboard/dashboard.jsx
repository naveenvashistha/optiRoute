import MetricCard from "./metricCard";
import TrafficFunnel from "./trafficFunnel";
import { useTelemetry } from "../../context/metrics";
import { formatCurrency, formatNumber, formatPercentage } from "../../utils/formatter";

export default function Dashboard({ onClose }) {
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
    <div className="flex flex-col h-full w-full max-w-sm xl:max-w-md p-5 gap-3 bg-[#1e2330]/40 border-l border-slate-700/50 overflow-y-auto">
      
      {/* 2x2 Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <MetricCard
          title="Est. Cost Saved"
          value={formatCurrency(stats.costSavedUsd)}
          subtitle="vs. 100% Cloud API"
          valueColor="text-emerald-400"
          type="cost"
        />

        <MetricCard
          title="Tokens Offloaded"
          value={formatNumber(stats.tokensOffloaded)}
          subtitle="Via Cache & Local SLM"
          valueColor="text-purple-400"
          type="tokens"
        />

        <MetricCard
          title="Avg Response Time"
          value={`${avgLatency}ms`}
          subtitle="Blended across all routes"
          valueColor="text-sky-400"
          type="time"
        />

        <MetricCard
          title="Bypass Intent Rate"
          value={formatPercentage(bypassRate)}
          subtitle="MLP Classifier output"
          valueColor="text-amber-400"
          type="intent"
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