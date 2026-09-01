// src/App.jsx
import Dashboard from "./component/dashboard/dashboard";

export default function App() {
  return (
    <div className="min-h-screen bg-[#0a0f1d] text-slate-100 flex flex-col antialiased">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-[#0f172a]/50 backdrop-blur-md px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <h1 className="font-bold tracking-wide text-base text-white">
            OptiRoute Gateway
          </h1>
        </div>
        <span className="text-xs font-mono text-slate-400 bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded-md">
          Session Metrics: Active
        </span>
      </header>

      {/* Main Container */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-7xl mx-auto w-full items-start">

        {/* left Column: Chat Playground Slot */}
        <section className="lg:col-span-7 h-[640px] bg-[#111827]/40 border border-slate-800/80 rounded-xl p-6 flex flex-col justify-center items-center text-slate-500 border-dashed">
          <p className="text-sm font-medium text-slate-400">Chat Container Slot</p>
          <p className="text-xs text-slate-600 mt-1">
            Mount the chat interface component here.
          </p>
        </section>

        {/* right Column: Telemetry Dashboard */}
        <section className="lg:col-span-5 flex justify-center lg:justify-start">
          <Dashboard />
        </section>
      </main>
    </div>
  );
}