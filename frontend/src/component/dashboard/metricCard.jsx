// src/components/dashboard/MetricCard.jsx

function MetricCard({ title, value, subtitle, valueColor = "text-white" }) {
  return (
    <div className="bg-[#111827]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-sm flex flex-col justify-between">
      <div className="text-[11px] font-bold tracking-wider text-slate-400 uppercase">
        {title}
      </div>
      
      <div className={`text-3xl font-extrabold my-2 tracking-tight ${valueColor}`}>
        {value}
      </div>
      
      <div className="text-xs text-slate-500 font-medium">
        {subtitle}
      </div>
    </div>
  );
}

export default MetricCard;