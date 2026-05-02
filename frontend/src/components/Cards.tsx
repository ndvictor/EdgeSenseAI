import type { EdgeSignal, Recommendation } from "@/lib/api";

export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-2">
      <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-emerald-500">{eyebrow}</p>
      <h1 className="mt-0.5 text-lg font-semibold leading-tight text-slate-950">{title}</h1>
      <p className="mt-0.5 max-w-5xl text-xs leading-snug text-slate-950/80">{description}</p>
    </div>
  );
}

export function MetricCard({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2">
      <span className="block truncate text-[10px] font-semibold uppercase tracking-wide text-emerald-600">{label}</span>
      <div className={accent ? "mt-1 truncate text-lg font-bold leading-tight text-white/90" : "mt-1 truncate text-lg font-bold leading-tight text-white/80"}>{value}</div>
    </div>
  );
}

export function RecommendationTable({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <div className="mt-1 overflow-x-auto rounded-xl border border-slate-600 bg-slate-900 p-2">
      <table className="w-full min-w-[900px] text-left text-xs">
        <thead className="bg-slate-900 text-[10px] uppercase tracking-wide text-emerald-600">
          <tr>
            <th className="px-2 py-2">Symbol</th>
            <th className="px-2 py-2">Asset</th>
            <th className="px-2 py-2">Horizon</th>
            <th className="px-2 py-2">Decision</th>
            <th className="px-2 py-2">Score</th>
            <th className="px-2 py-2">Confidence</th>
            <th className="px-2 py-2">R/R</th>
            <th className="px-2 py-2">Reason</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800 bg-slate-900">
          {recommendations.map((rec) => (
            <tr key={`${rec.symbol}-${rec.horizon}`} className="hover:bg-emerald-950/30">
              <td className="px-2 py-1.5"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-cyan-500">{rec.symbol}</span></td>
              <td className="px-2 py-1.5"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-cyan-500">{rec.asset_class}</span></td>
              <td className="px-2 py-1.5"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] font-semibold uppercase text-emerald-300">{rec.horizon}</span></td>
              <td className="px-2 py-1.5"><span className="rounded-full border border-cyan-400 bg-blue-700/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-blue-500">{rec.final_decision}</span></td>
              <td className="px-2 py-1.5"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-blue-500">{rec.final_score}</span></td>
              <td className="px-2 py-1.5"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-bold text-blue-500">{Math.round(rec.confidence * 100)}%</span></td>
              <td className="px-2 py-1.5"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-1.5 py-0.5 text-[10px] text-emerald-300">{rec.reward_risk_ratio.toFixed(1)}R</span></td>
              <td className="max-w-xl px-2 py-1.5 text-[11px] leading-snug text-emerald-500">{rec.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function EdgeSignalGrid({ signals }: { signals: EdgeSignal[] }) {
  return (
    <div className="grid grid-cols-1 gap-2 xl:grid-cols-3">
      {signals.map((signal) => (
        <div key={`${signal.symbol}-${signal.signal_type}`} className="rounded-xl border border-slate-800 bg-slate-900 p-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate text-[10px] uppercase text-emerald-600">{signal.signal_name}</p>
              <h3 className="mt-0.5 text-lg font-semibold leading-tight text-emerald-600">{signal.symbol}</h3>
            </div>
            <span className="rounded-full bg-violet-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-violet-300">{signal.urgency}</span>
          </div>
          <div className="mt-2 grid grid-cols-3 gap-1.5 text-xs">
            <Mini label="Score" value={signal.edge_score} />
            <Mini label="Conf" value={`${Math.round(signal.confidence * 100)}%`} />
            <Mini label="Decay" value={signal.time_decay} />
          </div>
          <p className="mt-2 text-xs leading-snug text-slate-400">{signal.recommended_action}</p>
          <p className="mt-1 text-xs leading-snug text-slate-400">{signal.reason}</p>
        </div>
      ))}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-emerald-900 bg-slate-900/20 p-2">
      <p className="text-[9px] uppercase tracking-wide text-emerald-600">{label}</p>
      <p className="mt-0.5 truncate text-sm font-bold text-emerald-600">{value}</p>
    </div>
  );
}
