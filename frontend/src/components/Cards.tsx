import type { EdgeSignal, Recommendation } from "@/lib/api";

export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    
    <div className="mb-6">
      <p className="text-xs uppercase tracking-[0.28em] text-emerald-500">{eyebrow}</p>
      <h1 className="mt-1 text-4xl font-black text-slate-950 texts-center">{title}</h1>
      <p className="mt-1 max-w-4xl text-sm text-slate-950 ">{description}</p>
    </div>
  );
}

export function MetricCard({ label, value, accent = false }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-900 px-6 py-6 w-62">
      <span className="text-xl uppercase text-emerald-600">{label}</span>
      <div className={accent ? "mt-2 text-2xl font-black text-white/80 text-center" : "mt-2 text-2xl font-black text-white/80 text-center"}>{value}</div>
    </div>
  );
}

export function RecommendationTable({ recommendations }: { recommendations: Recommendation[] }) {
  return (
    <div className="mt-2 rounded-2xl border border-slate-600 bg-slate-900 p-4">
      <table className="min-w-[900px] text-left text-sm ">
        <thead className="min-w-[900px]  bg-slate-900 text-md uppercase tracking-wide text-emerald-600 px-4 p-4">
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
        <tbody className="mt-1 rounded-2xl bg-slate-900">
          {recommendations.map((rec) => (
            <tr key={`${rec.symbol}-${rec.horizon}`} className=" hover:bg-emerald-950/30">
              <td className="px-2 py-1"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-2 py-1 text-xs font-semibold uppercase text-cyan-500">{rec.symbol}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-1 py-1 text-xs font-semibold uppercase text-cyan-500">{rec.asset_class}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-1 py-1 text-xs font-semibold uppercase text-emerald-300">{rec.horizon}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-cyan-400 bg-blue-700/10 px-2 py-1 text-xs font-semibold uppercase text-blue-500">{rec.final_decision}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-blue-500">{rec.final_score}</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-1 text-xs font-bold text-blue-500">{Math.round(rec.confidence * 100)}%</span></td>
              <td className="px-4 py-3"><span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-1 py-1 text-xs text-emerald-300">{rec.reward_risk_ratio.toFixed(1)}R</span></td>
              <td className="px-4 py-3 text-s text-emerald-500">{rec.reason}</td>
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
        <div key={`${signal.symbol}-${signal.signal_type}`} className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs uppercase text-emerald-600">{signal.signal_name}</p>
              <h3 className="mt-1 text-2xl text-emerald-600">{signal.symbol}</h3>
            </div>
            <span className="rounded-full bg-violet-500/10 px-2 py-1 text-xs font-bold uppercase text-violet-300">{signal.urgency}</span>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-md">
            <Mini label="Score" value={signal.edge_score} />
            <Mini label="Conf" value={`${Math.round(signal.confidence * 100)}%`} />
            <Mini label="Decay" value={signal.time_decay} />
          </div>
          <p className="mt-3 text-sm text-slate-400">{signal.recommended_action}</p>
          <p className="mt-3 text-sm text-slate-400">{signal.reason}</p>
        </div>
      ))}
    </div>
  );
}

function Mini({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-emerald-900 bg-slate-900/20 p-3">
      <p className="text-[10px] uppercase tracking-wide text-emerald-600">{label}</p>
      <p className="mt-1 text-xl font-black text-emerald-600">{value}</p>
    </div>
  );
}
