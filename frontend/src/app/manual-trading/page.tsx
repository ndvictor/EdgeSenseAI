import Link from "next/link";

const links = [
  ["TradeNow Manual UI", "/tradenow", "Manual paper execution interface and operator-controlled trading actions."],
  ["Trading Desk", "/trading-desk", "Manual trading desk views and legacy workflow support."],
  ["Command Center", "/command-center", "Manual decision and research cockpit for candidate ranking."],
  ["Candidate Engine", "/candidate-engine", "Manual research pipeline for candidate sources and signals."],
  ["Candidate Universe", "/candidates", "Manual candidate list management and decision workflow tools."],
  ["Edge Signals", "/edge-signals", "Signal review surface for research and manual workflows."],
  ["Auto Execution Monitor", "/auto-execution-monitor", "Monitoring surface for legacy/manual automation gates."],
];

export default function ManualTradingPage() {
  return (
    <main className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <div className="mb-3 inline-flex rounded-full border border-sky-400/30 bg-sky-400/10 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.2em] text-sky-200">
          Legacy Manual Trading
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Legacy Manual Trading</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
          Manual research, candidate management, command center, TradeNow, and legacy operator tools.
        </p>
      </div>

      <section className="mb-6 rounded-2xl border border-sky-400/25 bg-sky-500/10 px-4 py-3 text-sm leading-6 text-sky-100">
        These are manual/research/legacy tools. They are not the autonomous workflow controller.
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {links.map(([title, href, description]) => (
          <Link key={href} href={href} className="rounded-2xl border border-sky-400/15 bg-[#070c12]/95 p-4 transition hover:border-sky-400/35">
            <div className="text-lg font-semibold text-slate-50">{title}</div>
            <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
            <div className="mt-4 text-xs font-semibold text-sky-300">Open →</div>
          </Link>
        ))}
      </section>
    </main>
  );
}
