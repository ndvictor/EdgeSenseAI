"use client";

import { useEffect, useState } from "react";
import {
  getPromotionModelsStatus,
  getPromotionStrategiesStatus,
  type PromotionModelRow,
  type PromotionStrategyRow,
} from "@/lib/api";

export type PromotionCenterActiveSection = "overview" | "requirements" | "strategy" | "models";

function fmt(v: string | number | boolean | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

function PromotionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-black/35 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.32)] backdrop-blur-xl">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</h3>
          {subtitle ? <p className="mt-1 text-xs leading-5 text-slate-500">{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </section>
  );
}

export function PromotionCenterPanel({ activeSection }: { activeSection: PromotionCenterActiveSection }) {
  const [strategies, setStrategies] = useState<PromotionStrategyRow[]>([]);
  const [models, setModels] = useState<PromotionModelRow[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, m] = await Promise.all([getPromotionStrategiesStatus(), getPromotionModelsStatus()]);
        if (!cancelled) {
          setStrategies(s.strategies ?? []);
          setModels(m.models ?? []);
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setStrategies([]);
          setModels([]);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (activeSection === "overview") {
    return null;
  }

  const safety = (
    <div className="rounded-xl border border-cyan-400/25 bg-cyan-950/35 px-4 py-3 text-sm text-cyan-100">
      <strong className="font-semibold text-cyan-50">Safety:</strong> Promotion views are evidence and readiness only. They do not submit orders,
      enable live trading, or activate strategies automatically.
    </div>
  );

  if (activeSection === "requirements") {
    return (
      <PromotionCard
        title="Promotion requirements"
        subtitle="Rules rows are checked against evidence.metrics. Missing metrics stay not_ready."
      >
        <div className="space-y-4">
          {safety}
          {loading ? (
            <p className="text-sm text-slate-400">Loading promotion readiness…</p>
          ) : error ? (
            <div className="rounded-xl border border-rose-700/50 bg-rose-950/40 px-4 py-3 text-sm text-rose-100">
              No promotion evidence available yet.
              <span className="mt-2 block text-xs text-rose-200/90">{error}</span>
            </div>
          ) : null}
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.04] p-4">
            <p className="text-sm text-slate-400">Each strategy and model row is evaluated with the thresholds below.</p>
            <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-slate-300 [&>li]:marker:text-cyan-400/80">
              <li>sample_size ≥ 50</li>
              <li>avg_r &gt; 0.10</li>
              <li>profit_factor &gt; 1.25</li>
              <li>max_drawdown_r &gt; −8R (better than −8R)</li>
              <li>rule_violations = 0</li>
              <li>spread_slippage_acceptable = true</li>
              <li>small_account_feasible = true</li>
            </ul>
            <p className="mt-3 text-xs text-slate-500">
              Models additionally require validation_score, calibration_status, and prediction_error_r in evidence.metrics.
            </p>
          </div>
        </div>
      </PromotionCard>
    );
  }

  if (activeSection === "strategy") {
    return (
      <PromotionCard
        title="Strategy promotion"
        subtitle="Strategy keys, metrics, blockers, and promotion_readiness from stored evidence."
      >
        <div className="space-y-4">
          {safety}
          {loading ? <p className="text-sm text-slate-400">Loading strategy promotion rows…</p> : null}
          {!loading && error ? (
            <div className="rounded-xl border border-rose-700/50 bg-rose-950/40 px-4 py-3 text-sm text-rose-100">
              Could not load strategy promotion rows.
              <span className="mt-2 block text-xs text-rose-200/90">{error}</span>
            </div>
          ) : null}
          {!loading && !error && strategies.length === 0 ? (
            <p className="rounded-xl border border-cyan-400/10 bg-black/20 px-4 py-3 text-sm text-slate-400">No strategy promotion rows yet.</p>
          ) : null}
          {!loading && !error && strategies.length > 0 ? (
            <div className="overflow-x-auto rounded-2xl border border-cyan-400/15 bg-black/25">
              <table className="w-full min-w-[1200px] border-collapse text-left text-sm">
                <thead className="border-b border-cyan-400/20 bg-cyan-400/[0.06] text-[10px] font-bold uppercase tracking-wider text-cyan-200/90">
                  <tr>
                    <th className="py-2.5 pl-3 pr-3">strategy_key</th>
                    <th className="py-2.5 pr-3">display_name</th>
                    <th className="py-2.5 pr-3">setup_type</th>
                    <th className="py-2.5 pr-3">status</th>
                    <th className="py-2.5 pr-3">sample_size</th>
                    <th className="py-2.5 pr-3">avg_r</th>
                    <th className="py-2.5 pr-3">profit_factor</th>
                    <th className="py-2.5 pr-3">max_dd_r</th>
                    <th className="py-2.5 pr-3">violations</th>
                    <th className="py-2.5 pr-3">spread_ok</th>
                    <th className="py-2.5 pr-3">small_acct</th>
                    <th className="py-2.5 pr-3">readiness</th>
                    <th className="py-2.5 pr-3">blockers</th>
                    <th className="py-2.5 pr-3">next_action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-400/10 text-slate-300">
                  {strategies.map((r) => (
                    <tr key={r.strategy_key} className="transition-colors hover:bg-cyan-400/[0.04]">
                      <td className="py-2.5 pl-3 pr-3 font-mono text-xs text-cyan-100/90">{r.strategy_key}</td>
                      <td className="py-2.5 pr-3">{r.display_name}</td>
                      <td className="py-2.5 pr-3">{r.setup_type}</td>
                      <td className="py-2.5 pr-3">{r.status}</td>
                      <td className="py-2.5 pr-3">{fmt(r.sample_size)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.avg_r)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.profit_factor)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.max_drawdown_r)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.rule_violations)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.spread_slippage_acceptable)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.small_account_feasible)}</td>
                      <td className="py-2.5 pr-3 font-semibold text-cyan-200">{r.promotion_readiness}</td>
                      <td className="max-w-xs py-2.5 pr-3 text-xs text-amber-200/90">{r.blockers.join(", ") || "—"}</td>
                      <td className="max-w-md py-2.5 pr-3 text-xs text-slate-400">{r.next_action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </PromotionCard>
    );
  }

  if (activeSection === "models") {
    return (
      <PromotionCard
        title="Model promotion"
        subtitle="Model keys, validation metrics, and promotion_readiness from stored evidence."
      >
        <div className="space-y-4">
          {safety}
          {loading ? <p className="text-sm text-slate-400">Loading model promotion rows…</p> : null}
          {!loading && error ? (
            <div className="rounded-xl border border-rose-700/50 bg-rose-950/40 px-4 py-3 text-sm text-rose-100">
              Could not load model promotion rows.
              <span className="mt-2 block text-xs text-rose-200/90">{error}</span>
            </div>
          ) : null}
          {!loading && !error && models.length === 0 ? (
            <p className="rounded-xl border border-cyan-400/10 bg-black/20 px-4 py-3 text-sm text-slate-400">No model promotion rows yet.</p>
          ) : null}
          {!loading && !error && models.length > 0 ? (
            <div className="overflow-x-auto rounded-2xl border border-cyan-400/15 bg-black/25">
              <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
                <thead className="border-b border-cyan-400/20 bg-cyan-400/[0.06] text-[10px] font-bold uppercase tracking-wider text-cyan-200/90">
                  <tr>
                    <th className="py-2.5 pl-3 pr-3">model_key</th>
                    <th className="py-2.5 pr-3">model_role</th>
                    <th className="py-2.5 pr-3">status</th>
                    <th className="py-2.5 pr-3">allowed_strategy_keys</th>
                    <th className="py-2.5 pr-3">sample_size</th>
                    <th className="py-2.5 pr-3">validation_score</th>
                    <th className="py-2.5 pr-3">calibration</th>
                    <th className="py-2.5 pr-3">pred_err_r</th>
                    <th className="py-2.5 pr-3">readiness</th>
                    <th className="py-2.5 pr-3">blockers</th>
                    <th className="py-2.5 pr-3">next_action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cyan-400/10 text-slate-300">
                  {models.map((r) => (
                    <tr key={r.model_key} className="transition-colors hover:bg-cyan-400/[0.04]">
                      <td className="py-2.5 pl-3 pr-3 font-mono text-xs text-cyan-100/90">{r.model_key}</td>
                      <td className="py-2.5 pr-3">{r.model_role}</td>
                      <td className="py-2.5 pr-3">{r.status}</td>
                      <td className="py-2.5 pr-3 text-xs">{r.allowed_strategy_keys.length ? r.allowed_strategy_keys.join(", ") : "—"}</td>
                      <td className="py-2.5 pr-3">{fmt(r.sample_size)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.validation_score)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.calibration_status)}</td>
                      <td className="py-2.5 pr-3">{fmt(r.prediction_error_r)}</td>
                      <td className="py-2.5 pr-3 font-semibold text-cyan-200">{r.promotion_readiness}</td>
                      <td className="max-w-xs py-2.5 pr-3 text-xs text-amber-200/90">{r.blockers.join(", ") || "—"}</td>
                      <td className="max-w-md py-2.5 pr-3 text-xs text-slate-400">{r.next_action}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </PromotionCard>
    );
  }

  return null;
}
