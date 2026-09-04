/**
 * Application Root Component (App.jsx)
 * ====================================
 * Serves as the primary layout wrapper for the OptiRoute Gateway.
 * Manages the global state for the slide-out Telemetry Dashboard
 * and handles the responsive flex-box layout transitions between
 * the chat interface and the metrics view.
 */

import React, { useState } from "react";
import ChatInterface from "./component/chat/ChatInterface";
import "./App.css";

function App() {
  // Tracks the visibility state of the side telemetry dashboard
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);

  return (
    // ── Master App Container ──
    // Forces the app to take up exactly 100% of the viewport height, preventing body scroll.
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        backgroundColor: "#000000",
      }}
    >
      {/* ── Top Navigation Bar ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "1rem 2rem",
          backgroundColor: "#111111",
          borderBottom: "1px solid #333333",
        }}
      >
        <h2 style={{ margin: 0, color: "#f8fafc", fontSize: "1.25rem" }}>
          OptiRoute Gateway
        </h2>

        {/* Dashboard Toggle Button */}
        <button
          onClick={() => setIsDashboardOpen(!isDashboardOpen)}
          style={{
            backgroundColor: isDashboardOpen ? "#333333" : "#2563eb",
            color: "white",
            border: "none",
            borderRadius: "0.5rem",
            padding: "0.5rem 1rem",
            cursor: "pointer",
            fontWeight: "bold",
            transition: "0.2s",
          }}
          title={
            isDashboardOpen
              ? "Close Telemetry Dashboard"
              : "Open Telemetry Dashboard"
          }
        >
          {isDashboardOpen ? "Close Dashboard" : "View Telemetry"}
        </button>
      </div>

      {/* ── Main Content Area ── */}
      {/* Flex-grow ensures this takes up all remaining vertical space below the navbar */}
      <div style={{ display: "flex", flexGrow: 1, overflow: "hidden" }}>
        {/* ── Chat Interface Section ── */}
        {/* Dynamically resizes based on dashboard state using cubic-bezier for a smooth mechanical slide */}
        <div
          style={{
            width: isDashboardOpen ? "70%" : "100%",
            transition: "width 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            height: "100%",
          }}
        >
          <ChatInterface />
        </div>

        {/* ── Telemetry Dashboard Section ── */}
        {/* Hides completely when closed (0% width, 0 opacity), slides in when opened */}
        <div
          style={{
            width: isDashboardOpen ? "30%" : "0%",
            opacity: isDashboardOpen ? 1 : 0,
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            borderLeft: isDashboardOpen ? "1px solid #333333" : "none",
            backgroundColor: "#000000",
            color: "#94a3b8",
            overflow: "hidden", // CRITICAL: Prevents inner content from spilling out during the slide animation
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Inner container maintains a minimum width so content doesn't squish during transition */}
          <div style={{ padding: "2rem", width: "100%", minWidth: "300px" }}>
            <h3 style={{ color: "#e2e8f0", margin: "0 0 1rem 0" }}>
              Telemetry Dashboard
            </h3>
            <p>Naveen's metrics will mount here...</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
