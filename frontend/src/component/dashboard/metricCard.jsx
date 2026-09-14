import React from "react";

function MetricCard({ title, value, subtitle, valueColor = "text-white", type }) {
  const icons = {
    cost: {
      left: <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
      right: <svg className="w-16 h-16 text-emerald-500" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C7.58 2 4 3.79 4 6s3.58 4 8 4 8-1.79 8-4-3.58-4-8-4zm0 5c-3.87 0-6-1.18-6-2s2.13-2 6-2 6 1.18 6 2-2.13 2-6 2z" /><path d="M4 10.5c0 2.21 3.58 4 8 4s8-1.79 8-4v-2.12c-1.54.91-4.22 1.62-8 1.62-3.78 0-6.46-.71-8-1.62V10.5z" /><path d="M4 15.5c0 2.21 3.58 4 8 4s8-1.79 8-4v-2.12c-1.54.91-4.22 1.62-8 1.62-3.78 0-6.46-.71-8-1.62V15.5z" /></svg>
    },
    tokens: {
      left: <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>,
      right: <svg className="w-16 h-16 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1"><rect x="6" y="6" width="12" height="12" rx="2" /><path strokeLinecap="round" strokeLinejoin="round" d="M9 6V4m2 2V4m2 2V4m2 2V4M9 20v-2m2 2v-2m2 2v-2m2 2v-2M4 9h2m-2 2h2m-2 2h2m-2 2h2m16-6h-2m2 2h-2m2 2h-2m2 2h-2" /><rect x="10" y="10" width="4" height="4" rx="1" fill="currentColor" /></svg>
    },
    time: {
      left: <svg className="w-4 h-4 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>,
      right: <svg className="w-16 h-16 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1"><path strokeLinecap="round" strokeLinejoin="round" d="M3 12h4l3-8 4 16 3-8h4" /></svg>
    },
    intent: {
      left: <svg className="w-4 h-4 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>,
      right: <svg className="w-16 h-16 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1"><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path strokeLinecap="round" d="M8.5 13.5l7 4M8.5 10.5l7-4" /></svg>
    }
  };

  const { left, right } = icons[type] || {};

  return (
    <div className="bg-[#121419] border border-[#2a2d36] rounded-xl p-5 shadow-lg flex flex-col justify-between relative overflow-hidden min-h-[140px]">
      
      <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-wider text-slate-400 uppercase z-10 whitespace-nowrap">
        {left} {title}
      </div>
      
      <div className="flex flex-col justify-end mt-4 z-10">
        <div className={`text-4xl font-black tracking-tight ${valueColor}`}>
          {value}
        </div>
        <div className="text-[10px] text-slate-500 font-semibold mt-1 uppercase tracking-wider">
          {subtitle}
        </div>
      </div>

      {/* Subtle background watermark icon */}
      <div className="absolute -bottom-4 -right-4 opacity-10 pointer-events-none transform -rotate-6">
        {right}
      </div>
    </div>
  );
}

export default MetricCard;