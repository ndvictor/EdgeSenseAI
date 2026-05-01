import type { EdgeSignal, Recommendation } from "@/lib/api";

export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <div className="mb-6">
      <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">{eyebrow}</p>
      <h1 className="mt-1 text-3xl font-black text-white">{title}</h1>
      <p className="mt-2 max-w-4xl text-sm text-slate-400">{description}</p>
    </div>
  );
}

export function MetricCard({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={accent ? "mt-2 text-xl font-black text-emerald-300" : "mt-2 text-xl font-black text-white"}>{value}</p>
    </div>
  );
}

export function RecommendationTable({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/80">
      <table className="w-full min-w-[900px] text-left text-sm">
        <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-400">
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
        <tbody className="divide-y divide-white/10">
          {recommendations.map((rec) => (
            <tr key={`${rec.symbol}-${rec.horizon}`} className="hover:bg-white/[0.04]">
              <td className="px-4 py-3 font-black text-cyan-300">{rec.symbol}</td>
              <td className="px-4 py-3 capitalize text-slate-300">{rec.asset_class}</td>
              <td className="px-4 py-3 text-slate-300">{rec.horizon}</td>
              <td className="px-4 py-3"><span className="rounded-full bg-blue-500/10 px-2 py-1 text-xs font-semibold uppercase text-blue-300">{rec.final_decision}</span></td>
              <td className="px-4 py-3 font-bold text-emerald-300">{rec.final_score}</td>
              <td className="px-4 py-3 font-bold text-white">{Math.round(rec.confidence * 100)}%</td>
              <td className="px-4 py-3 text-slate-300">{rec.reward_risk_ratio.toFixed(1)}R</td>
              <td className="max-w-xl px-4 py-3 text-xs text-slate-400">{rec.reason}</td>
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
        <div key={`${signal.symbol}-${signal.signal_type}`} className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">{signal.signal_name}</p>
              <h3 className="mt-1 text-2xl font-black text-white">{signal.symbol}</h3>
            </div>
            <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs font-bold uppercase text-amber-300">{signal.urgency}</span>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-sm">
            <Mini label="Score" value={signal.edge_score} />
            <Mini label="Conf" value={`${Math.round(signal.confidence * 100)}%`} />
            <Mini label="Decay" value={signal.time_decay} />
          </div>
          <p className="mt-4 text-sm text-slate-300">{signal.recommended_action}</p>
          <p className="mt-2 text-xs text-slate-500">{signal.reason}</p>
        </div>
      ))}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-white/10 bg-slate-950/70 p-3">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-white">{value}</p>
    </div>
  );
}
