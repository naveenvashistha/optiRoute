import React from "react";

function MetricCard({ title, value, subtitle, valueColor = "text-white", type }) {
  // SVG Map based on the reference image structure
  const icons = {
    cost: {
      left: (
        <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      right: (
        <svg className="w-8 h-8 text-emerald-500 opacity-80" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 2C7.58 2 4 3.79 4 6s3.58 4 8 4 8-1.79 8-4-3.58-4-8-4zm0 5c-3.87 0-6-1.18-6-2s2.13-2 6-2 6 1.18 6 2-2.13 2-6 2z" />
          <path d="M4 10.5c0 2.21 3.58 4 8 4s8-1.79 8-4v-2.12c-1.54.91-4.22 1.62-8 1.62-3.78 0-6.46-.71-8-1.62V10.5z" />
          <path d="M4 15.5c0 2.21 3.58 4 8 4s8-1.79 8-4v-2.12c-1.54.91-4.22 1.62-8 1.62-3.78 0-6.46-.71-8-1.62V15.5z" />
        </svg>
      )
    },
    tokens: {
      left: null,
      right: (
        <svg className="w-8 h-8 text-purple-400 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <rect x="6" y="6" width="12" height="12" rx="2" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 6V4m2 2V4m2 2V4m2 2V4M9 20v-2m2 2v-2m2 2v-2m2 2v-2M4 9h2m-2 2h2m-2 2h2m-2 2h2m16-6h-2m2 2h-2m2 2h-2m2 2h-2" />
          <rect x="10" y="10" width="4" height="4" rx="1" fill="currentColor" />
        </svg>
      )
    },
    time: {
      left: (
        <svg className="w-4 h-4 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      ),
      right: (
        <svg className="w-8 h-8 text-sky-400 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h4l3-8 4 16 3-8h4" />
        </svg>
      )
    },
    intent: {
      left: null,
      right: (
        <svg className="w-8 h-8 text-amber-400 opacity-80" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5">
          <circle cx="18" cy="5" r="3" />
          <circle cx="6" cy="12" r="3" />
          <circle cx="18" cy="19" r="3" />
          <path strokeLinecap="round" d="M8.5 13.5l7 4M8.5 10.5l7-4" />
        </svg>
      )
    }
  };

  const { left, right } = icons[type] || {};

  return (
    <div className="bg-[#111827]/80 border border-slate-700/50 rounded-xl p-4 shadow-lg flex flex-col justify-between relative overflow-hidden">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          {left} {title}
        </div>
      </div>
      
      <div className="flex items-end justify-between mt-3">
        <div>
          <div className={`text-3xl font-extrabold tracking-tight ${valueColor}`}>
            {value}
          </div>
          <div className="text-[10px] text-slate-500 font-medium mt-1 uppercase tracking-wider">
            {subtitle}
          </div>
        </div>
        <div className="mb-2">
          {right}
        </div>
      </div>
    </div>
  );
}

export default MetricCard;