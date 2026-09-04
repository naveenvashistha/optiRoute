/**
 * Application Root Component (App.jsx)
 * ====================================
 * Serves as the primary layout wrapper for the OptiRoute Gateway.
 * Merges the GitHub team's Tailwind aesthetics & Dashboard component
 * with the local dynamic sliding-state layout engine.
 */

import React, { useState } from "react";
import ChatInterface from "./component/chat/ChatInterface";
import Dashboard from "./component/dashboard/dashboard";
import "./App.css";

export default function App() {
  // Tracks the visibility state of the side telemetry dashboard
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);

  return (
    // ── Master App Container ──
    <div className="min-h-screen bg-[#0a0f1d] text-slate-100 flex flex-col antialiased overflow-hidden">
      {/* ── Top Navbar (Merged Aesthetics) ── */}
      <header className="border-b border-slate-800/80 bg-[#0f172a]/50 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {/* GitHub Team's pulsing status indicator */}
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <h1 className="font-bold tracking-wide text-base text-white">
            OptiRoute Gateway
          </h1>
        </div>

        <div className="flex items-center gap-4">
          {/* GitHub Team's static metric badge */}
          <span className="hidden sm:block text-xs font-mono text-slate-400 bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded-md">
            Session Metrics: Active
          </span>

          {/* Local Team's Dynamic Toggle Button converted to Tailwind */}
          <button
            onClick={() => setIsDashboardOpen(!isDashboardOpen)}
            className={`px-4 py-2 rounded-md font-bold text-sm transition-colors duration-200 ${
              isDashboardOpen
                ? "bg-slate-800 text-white hover:bg-slate-700"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
            title={
              isDashboardOpen
                ? "Close Telemetry Dashboard"
                : "Open Telemetry Dashboard"
            }
          >
            {isDashboardOpen ? "Close Dashboard" : "View Telemetry"}
          </button>
        </div>
      </header>

      {/* ── Main Content Area (Local Sliding Engine) ── */}
      <div className="flex grow overflow-hidden">
        {/* ── Chat Interface Section ── */}
        <div
          style={{
            width: isDashboardOpen ? "70%" : "100%",
            transition: "width 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
          className="h-full"
        >
          <ChatInterface />
        </div>

        {/* ── Telemetry Dashboard Section ── */}
        <div
          style={{
            width: isDashboardOpen ? "30%" : "0%",
            opacity: isDashboardOpen ? 1 : 0,
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
          className="h-full border-l border-slate-800/80 bg-[#0f172a] overflow-hidden flex flex-col"
        >
          {/* Inner container maintains a minimum width so the GitHub Dashboard doesn't squish during transition */}
          <div className="w-full min-w-[320px] h-full overflow-y-auto p-2">
            {/* Mounting the GitHub Team's actual Dashboard component */}
            <Dashboard />
          </div>
        </div>
      </div>
    </div>
  );
}
