import React, { useState } from "react";
import ChatInterface from "./component/chat/ChatInterface";
import Dashboard from "./component/dashboard/dashboard";
import "./App.css";

export default function App() {
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);

  return (
    // 1. Root Container - Pure Black body
    <div className="h-screen w-screen bg-black text-[#F5E7C1] flex flex-col overflow-hidden font-sans">
      {/* 2. Top Navbar - Dark metallic slate gradient with a crisp bottom border */}
      <header
        className="shrink-0 h-[72px] bg-gradient-to-r from-[#1c1f26] via-[#14161b] to-[#0a0c0f] border-b border-[#2a2d36] flex items-center justify-between z-20 shadow-md"
        style={{ paddingLeft: "2rem", paddingRight: "2rem" }}
      >
        {/* Unboxed App Header - Warm Gold Text */}
        <div className="flex items-center">
          <h1 className="font-extrabold tracking-wide text-xl text-[#D4AF37]">
            OptiRoute Gateway
          </h1>
        </div>

        {/* Right Side Container */}
        <div className="flex items-center" style={{ gap: "1.25rem" }}>
          {/* Session Badge - Re-added as a thin gold-bordered pill matching the image */}
          {/* <span
            className="hidden sm:inline-flex items-center justify-center text-[10px] font-bold uppercase tracking-widest text-[#D4AF37] border border-[#D4AF37]/50 rounded-full bg-[#D4AF37]/5"
            style={{
              paddingLeft: "1rem",
              paddingRight: "1rem",
              paddingTop: "0.4rem",
              paddingBottom: "0.4rem",
            }}
          >
            SESSION: ACTIVE
          </span> */}
          {/* Dashboard Button - Transparent background with gold text and icon */}
          <button
            onClick={() => setIsDashboardOpen(!isDashboardOpen)}
            className={`inline-flex items-center justify-center gap-2 py-2 min-h-[44px] rounded-full text-sm font-bold transition-all duration-200 shadow-md ${
              isDashboardOpen
                ? "bg-[#222222] text-[#D4AF37] hover:bg-[#333333]"
                : "bg-[#D4AF37] text-[#11100D] hover:bg-[#F5E7C1]"
            }`}
            style={{ paddingLeft: "1.5rem", paddingRight: "1.5rem" }}
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2.5"
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            {isDashboardOpen ? "Close Dashboard" : "Open Dashboard"}
          </button>
        </div>
      </header>

      {/* 3. Main Flex Canvas */}
      <main className="flex-1 flex overflow-hidden relative w-full">
        {/* 4. Chat Panel */}
        <div className="flex-1 flex flex-col h-full bg-black relative z-10 transition-all duration-300">
          <ChatInterface />
        </div>

        {/* 5. Dashboard Drawer - Subtle dark border to separate it from the chat when open */}
        <div
          className={`h-full border-l border-[#222222] bg-black transition-all duration-300 ease-in-out z-20 flex flex-col shrink-0 ${
            isDashboardOpen
              ? "w-[380px] opacity-100"
              : "w-0 opacity-0 border-none"
          }`}
        >
          <div className="w-[380px] h-full overflow-y-auto p-6">
            <Dashboard />
          </div>
        </div>
      </main>
    </div>
  );
}
