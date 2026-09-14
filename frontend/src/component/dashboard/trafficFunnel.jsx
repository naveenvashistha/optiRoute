import { formatPercentage } from "../../utils/formatter";

function TrafficFunnel({ totalReqs, hits, local, cloud }) {
  const cacheHitRate = totalReqs > 0 ? hits / totalReqs : 0;
  const localRate = totalReqs > 0 ? local / totalReqs : 0;
  const cloudRate = totalReqs > 0 ? cloud / totalReqs : 0;

  return (
    <div className="bg-[#121419] border border-[#2a2d36] rounded-xl p-5 shadow-lg relative overflow-hidden">
      <div className="text-[11px] font-bold tracking-wider text-slate-400 uppercase mb-5 flex items-center gap-2">
        <svg className="w-4 h-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
        </svg>
        Traffic Distribution Funnel
      </div>

      <div className="mb-5">
        <div className="flex justify-between text-xs font-bold mb-2">
          <span className="text-slate-300">Semantic Cache Hits</span>
          <span className="text-emerald-400">{formatPercentage(cacheHitRate)}</span>
        </div>
        <div className="w-full h-2.5 bg-[#1a1d24] rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 transition-all duration-500 ease-out rounded-full shadow-[0_0_10px_rgba(16,185,129,0.4)]"
            style={{ width: formatPercentage(cacheHitRate) }}
          />
        </div>
      </div>

      <div className="mb-6">
        <div className="flex justify-between text-xs font-bold mb-2">
          <span className="text-slate-300">Shadow Router</span>
          <span className="text-slate-200">
            <span className="text-blue-400">{formatPercentage(localRate)}</span> Local / <span className="text-rose-400">{formatPercentage(cloudRate)}</span> Cloud
          </span>
        </div>
        <div className="w-full h-2.5 bg-[#1a1d24] rounded-full overflow-hidden flex">
          <div
            className="h-full bg-blue-500 transition-all duration-500 ease-out shadow-[0_0_10px_rgba(59,130,246,0.4)]"
            style={{ width: `${localRate * 100}%` }}
          />
          <div
            className="h-full bg-rose-500 transition-all duration-500 ease-out shadow-[0_0_10px_rgba(244,63,94,0.4)]"
            style={{ width: `${cloudRate * 100}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] font-bold pt-4 border-t border-[#2a2d36] text-slate-400 uppercase tracking-wider">
        <div>
          Total Reqs: <span className="text-white ml-1 text-sm">{totalReqs}</span>
        </div>
        <div className="flex gap-4">
          <span>Hits: <span className="text-emerald-400 ml-1 text-sm">{hits}</span></span>
          <span>Local: <span className="text-blue-400 ml-1 text-sm">{local}</span></span>
          <span>Cloud: <span className="text-rose-400 ml-1 text-sm">{cloud}</span></span>
        </div>
      </div>
    </div>
  );
}

export default TrafficFunnel;