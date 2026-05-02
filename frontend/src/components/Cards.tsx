import type { EdgeSignal, Recommendation } from "@/lib/api";

export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-4">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-500">{eyebrow}</p>
      <h1 className="mt-1 text-2xl font-bold leading-tight text-slate-950">{title}</h1>
      <p className="mt-1 max-w-6xl text-sm leading-relaxed text-slate-950/80">{description}</p>
    </div>
  );
}

export function MetricCard({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="w-full rounded-xl border border-slate-700 bg-slate-900 px-5 py-4">
      <span className="block truncate text-xs font-semibold uppercase tracking-wide text-emerald-600">{label}</span>
      <div className={accent ? "mt-2 truncate text-2xl font-bold leading-tight text-white/90" : "mt-2 truncate text-2xl font-bold leading-tight text-white/80"}>{value}</div>
    </div>
  );
}

export function RecommendationTable({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <div className="mt-2 overflow-x-auto rounded-xl border border-slate-600 bg-slate-900 p-3">
      <table className="w-full min-w-[1200px] text-left text-sm">
        <thead className="bg-slate-900 text-xs uppercase tracking-wide text-emerald-600">
          <tr>
            <th className="px-4 py-3">Symbol</th>
            <th className="px-4 py-3">Asset</th>
            <th className="px-4 py-3">Horizon</th>
            <th className="px-4 py-3">Decision</th>
            <th className="px-4 py-3">Score</th>
            <th className="px-4 py-3">Confidence</th>
            <th className="px-4 py-3">R/R</th>
            <th className="px-4 py-3">Reason</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 bg-slate-900">
          {recommendations.map((rec) => (
            <tr key={`${rec.symbol}-${rec.horizon}`} className="hover:bg-emerald-950/30">
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-3 py-1 text-xs font-semibold uppercase text-cyan-500">{rec.symbol}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-2 py-1 text-xs font-semibold uppercase text-cyan-500">{rec.asset_class}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-1 text-xs font-semibold uppercase text-emerald-300">{rec.horizon}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-400 bg-blue-700/10 px-3 py-1 text-xs font-semibold uppercase text-blue-500">{rec.final_decision}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-blue-500">{rec.final_score}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-blue-500">{Math.round(rec.confidence * 100)}%</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-1 text-xs text-emerald-300">{rec.reward_risk_ratio.toFixed(1)}R</span></td>
              <td className="max-w-xl px-4 py-3 text-sm leading-relaxed text-emerald-500">{rec.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EdgeSignalGrid({ signals }: { signals: EdgeSignal[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      {signals.map((signal) => (
        <div key={`${signal.symbol}-${signal.signal_type}`} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-xs uppercase text-emerald-600">{signal.signal_name}</p>
              <h3 className="mt-1 text-2xl font-semibold leading-tight text-emerald-600">{signal.symbol}</h3>
            </div>
            <span className="rounded-full bg-violet-500/10 px-3 py-1 text-xs font-bold uppercase text-violet-300">{signal.urgency}</span>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-sm">
            <Mini label="Score" value={signal.edge_score} />
            <Mini label="Conf" value={`${Math.round(signal.confidence * 100)}%`} />
            <Mini label="Decay" value={signal.time_decay} />
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">{signal.recommended_action}</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-400">{signal.reason}</p>
        </div>
      ))}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-emerald-900 bg-slate-900/20 p-3">
      <p className="text-[10px] uppercase tracking-wide text-emerald-600">{label}</p>
      <p className="mt-1 truncate text-lg font-bold text-emerald-600">{value}</p>
    </div>
  );
}
