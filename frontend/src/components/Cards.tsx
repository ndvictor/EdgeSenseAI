import type { EdgeSignal, Recommendation } from "@/lib/api";

export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    
    <div className="mb-6">
      <p className="text-sm uppercase tracking-[0.28em] text-cyan-500">{eyebrow}</p>
      <h1 className="mt-1 text-xl font-black text-white">{title}</h1>
      <p className="mt-1 max-w-4xl text-sm text-emerald-500">{description}</p>
    </div>
  );
}

export function MetricCard({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-emerald-700 bg-slate-950 px-2 py-4 w-38">
      <span className="text-xl uppercase text-emerald-500">{label}</span>
      <div className={accent ? "mt-2 text-lg font-black text-emerald-600" : "mt-2 text-xl font-black text-white"}>{value}</div>
    </div>
  );
}

export function RecommendationTable({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <div className="mt-2 rounded-2xl border border-emerald-700 bg-slate-700/80 p-4">
      <table className="min-w-[900px] text-left text-sm ">
        <thead className="min-w-[900px]  bg-slate-700 text-sm uppercase tracking-wide text-emerald-400 px-4 p-4">
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
        <tbody className="mt-2 rounded-2xl bg-slate-950 divide-y-emerald-950">
          {recommendations.map((rec) => (
            <tr key={`${rec.symbol}-${rec.horizon}`} className=" hover:bg-emerald/10">
              <td className="px-2 py-1"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-2 py-1 text-xs font-semibold uppercase text-cyan-500">{rec.symbol}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-1 py-1 text-xs font-semibold uppercase text-cyan-500">{rec.asset_class}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-1 py-1 text-xs font-semibold uppercase text-emerald-300">{rec.horizon}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-400 bg-blue-700/10 px-2 py-1 text-xs font-semibold uppercase text-blue-500">{rec.final_decision}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-blue-500">{rec.final_score}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-1 text-xs font-bold text-blue-500">{Math.round(rec.confidence * 100)}%</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-1 py-1 text-xs text-emerald-300">{rec.reward_risk_ratio.toFixed(1)}R</span></td>
              <td className="px-4 py-3 text-s text-emerald-400">{rec.reason}</td>
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
        <div key={`${signal.symbol}-${signal.signal_type}`} className="rounded-2xl border border-white/10 bg-emerald-800/80 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-emerald-900">{signal.signal_name}</p>
              <h3 className="mt-1 text-2xl font-black text-white">{signal.symbol}</h3>
            </div>
            <span className="rounded-full bg-amber-500/10 px-2 py-1 text-xs font-bold uppercase text-amber-300">{signal.urgency}</span>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-md">
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
    <div className="rounded-xl border border-white/10 bg-slate-950 p-3">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-white">{value}</p>
    </div>
  );
}
