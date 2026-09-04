// src/components/dashboard/TrafficFunnel.jsx
import { formatPercentage } from "../../utils/formatter";

function TrafficFunnel({ totalReqs, hits, local, cloud }) {
  const cacheHitRate = totalReqs > 0 ? hits / totalReqs : 0;
  const localRate = totalReqs > 0 ? local / totalReqs : 0;
  const cloudRate = totalReqs > 0 ? cloud / totalReqs : 0;

  return (
    <div className="bg-[#111827]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-sm">
      <div className="text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-4">
        Traffic Distribution Funnel
      </div>

      {/* Row 1: Semantic Cache */}
      <div className="mb-4">
        <div className="flex justify-between text-xs font-semibold mb-1.5">
          <span className="text-slate-300">Semantic Cache Hits</span>
          <span className="text-slate-200">{formatPercentage(cacheHitRate)}</span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-400 transition-all duration-500 ease-out rounded-full"
            style={{ width: formatPercentage(cacheHitRate) }}
          />
        </div>
      </div>

      {/* Row 2: Shadow Router */}
      <div className="mb-5">
        <div className="flex justify-between text-xs font-semibold mb-1.5">
          <span className="text-slate-300">Shadow Router (Cache Misses)</span>
          <span className="text-slate-200">
            {formatPercentage(localRate)} Local / {formatPercentage(cloudRate)} Cloud
          </span>
        </div>
        <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden flex">
          <div
            className="h-full bg-blue-500 transition-all duration-500 ease-out"
            style={{ width: `${localRate * 100}%` }}
          />
          <div
            className="h-full bg-rose-500 transition-all duration-500 ease-out"
            style={{ width: `${cloudRate * 100}%` }}
          />
        </div>
      </div>

      {/* Footer Counters */}
      <div className="flex items-center justify-between text-xs font-semibold pt-3 border-t border-slate-800/60 text-slate-400">
        <div>
          Total Reqs: <span className="text-slate-200 font-bold">{totalReqs}</span>
        </div>
        <div className="flex gap-3">
          <span>Hits: <span className="text-emerald-400">{hits}</span></span>
          <span>Local: <span className="text-blue-400">{local}</span></span>
          <span>Cloud: <span className="text-rose-400">{cloud}</span></span>
        </div>
      </div>
    </div>
  );
}

export default TrafficFunnel;