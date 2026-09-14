import React, { useState } from "react";
import ChatInterface from "./component/chat/ChatInterface";
import Dashboard from "./component/dashboard/dashboard";
import "./App.css";

export default function App() {
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);

  return (
    <div className="h-screen w-screen bg-black text-[#F5E7C1] flex flex-col overflow-hidden font-sans">
      {/* Hide scrollbar globally for the drawer */}
      <style>{`
        .hide-scrollbar::-webkit-scrollbar { display: none; }
        .hide-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>

      <header
        className="shrink-0 h-[72px] bg-gradient-to-r from-[#1c1f26] via-[#14161b] to-[#0a0c0f] border-b border-[#2a2d36] flex items-center justify-between z-20 shadow-md px-8"
      >
        <div className="flex items-center">
          <h1 className="font-extrabold tracking-wide text-xl text-[#D4AF37]">
            OptiRoute Gateway
          </h1>
        </div>

        <div className="flex items-center gap-5">
          <button
            onClick={() => setIsDashboardOpen(!isDashboardOpen)}
            className={`inline-flex items-center justify-center gap-2 py-2 px-4 sm:px-6 min-h-[44px] rounded-full sm:text-sm text-xs font-bold transition-all duration-200 shadow-md ${
              isDashboardOpen
                ? "bg-[#222222] text-[#D4AF37] hover:bg-[#333333]"
                : "bg-[#D4AF37] text-[#11100D] hover:bg-[#F5E7C1]"
            }`}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span className="hidden sm:inline">
              {isDashboardOpen ? "Close Dashboard" : "Open Dashboard"}
            </span>
            <span className="sm:hidden">
              {isDashboardOpen ? "Close" : "Stats"}
            </span>
          </button>
        </div>
      </header>

      <main className="flex-1 flex overflow-hidden relative w-full">
        <div className="flex-1 flex flex-col h-full bg-black relative z-10 transition-all duration-300">
          <ChatInterface />
        </div>

        <div
          className={`h-full border-l border-[#222222] bg-[#0a0c0f] transition-all duration-300 ease-in-out z-20 flex flex-col shrink-0 absolute right-0 top-0 lg:static z-40 shadow-2xl lg:shadow-none ${
            isDashboardOpen ? "w-full sm:w-[440px] translate-x-0 opacity-100" : "w-full sm:w-[440px] lg:w-0 translate-x-full lg:translate-x-0 opacity-0 lg:border-none pointer-events-none"
          }`}
        >
          <div className="w-full h-full overflow-y-auto p-6 hide-scrollbar">
            <Dashboard />
          </div>
        </div>
      </main>
    </div>
  );
}