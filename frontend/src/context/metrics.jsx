// src/context/TelemetryContext.jsx

import { createContext, useContext, useState } from "react";

const TelemetryContext = createContext(null);

export function TelemetryProvider({ children }) {
  const [stats, setStats] = useState({
    totalRequests: 0,
    costSavedUsd: 0.0,
    tokensOffloaded: 0,
    totalLatencyMs: 0,
    bypassIntentCount: 0,
    routeCounts: {
      hits: 0,   // Semantic Cache
      local: 0,  // Local SLM
      cloud: 0,  // Cloud API
    },
  });

  const recordRequest = (telemetry) => {
    if (!telemetry) return;

    setStats((prev) => {
      const normalizedRoute = (telemetry.route || "").toUpperCase();

      let routeKey = "cloud";
      if (normalizedRoute.includes("CACHE")) {
        routeKey = "hits";
      } else if (
        normalizedRoute.includes("LOCAL_SLM")
      ) {
        routeKey = "local";
      }

      return {
        totalRequests: prev.totalRequests + 1,
        costSavedUsd: prev.costSavedUsd + (telemetry.cost_saved_usd || 0),
        tokensOffloaded: prev.tokensOffloaded + (telemetry.tokens_offloaded || 0),
        totalLatencyMs: prev.totalLatencyMs + (telemetry.latency_ms || 0),
        bypassIntentCount:
          prev.bypassIntentCount + telemetry.intent,
        routeCounts: {
          ...prev.routeCounts,
          [routeKey]: prev.routeCounts[routeKey] + 1,
        },
      };
    });
  };

  const resetStats = () => {
    setStats({
      totalRequests: 0,
      costSavedUsd: 0.0,
      tokensOffloaded: 0,
      totalLatencyMs: 0,
      bypassIntentCount: 0,
      routeCounts: { hits: 0, local: 0, cloud: 0 },
    });
  };

  return (
    <TelemetryContext.Provider value={{ stats, recordRequest, resetStats }}>
      {children}
    </TelemetryContext.Provider>
  );
}

export const useTelemetry = () => {
  const context = useContext(TelemetryContext);
  if (!context) {
    throw new Error("useTelemetry must be used within a TelemetryProvider");
  }
  return context;
};