"use client";

import { useEffect, useState } from "react";
import {
  getPromotionModelsStatus,
  getPromotionStrategiesStatus,
  type PromotionModelRow,
  type PromotionStrategyRow,
} from "@/lib/api";

function fmt(v: string | number | boolean | null | undefined): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  return String(v);
}

export function PromotionCenterPanel() {
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

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-600/40 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
        <strong className="font-semibold">Safety:</strong> Promotion Center is evidence/readiness only. It does not submit orders,
        enable live trading, or activate strategies automatically.
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading promotion readiness…</p>
      ) : error ? (
        <div className="rounded-xl border border-rose-700/50 bg-rose-950/40 px-4 py-3 text-sm text-rose-100">
          No promotion evidence available yet.
          <span className="mt-2 block text-xs text-rose-200/90">{error}</span>
        </div>
      ) : strategies.length === 0 && models.length === 0 ? (
        <p className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-sm text-slate-400">
          No promotion evidence available yet.
        </p>
      ) : null}

      <section className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-sm">
        <h3 className="text-lg font-semibold text-emerald-400">Promotion requirements</h3>
        <p className="mt-2 text-sm text-slate-400">
          Rows evaluate against evidence.metrics only. Missing metrics stay not_ready.
        </p>
        <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-slate-300">
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
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-sm">
        <h3 className="mb-3 text-lg font-semibold text-emerald-400">Strategy promotion</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1200px] border-collapse text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-emerald-600">
              <tr>
                <th className="py-2 pr-3">strategy_key</th>
                <th className="py-2 pr-3">display_name</th>
                <th className="py-2 pr-3">setup_type</th>
                <th className="py-2 pr-3">status</th>
                <th className="py-2 pr-3">sample_size</th>
                <th className="py-2 pr-3">avg_r</th>
                <th className="py-2 pr-3">profit_factor</th>
                <th className="py-2 pr-3">max_dd_r</th>
                <th className="py-2 pr-3">violations</th>
                <th className="py-2 pr-3">spread_ok</th>
                <th className="py-2 pr-3">small_acct</th>
                <th className="py-2 pr-3">readiness</th>
                <th className="py-2 pr-3">blockers</th>
                <th className="py-2 pr-3">next_action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {strategies.map((r) => (
                <tr key={r.strategy_key}>
                  <td className="py-2 pr-3 font-mono text-xs">{r.strategy_key}</td>
                  <td className="py-2 pr-3">{r.display_name}</td>
                  <td className="py-2 pr-3">{r.setup_type}</td>
                  <td className="py-2 pr-3">{r.status}</td>
                  <td className="py-2 pr-3">{fmt(r.sample_size)}</td>
                  <td className="py-2 pr-3">{fmt(r.avg_r)}</td>
                  <td className="py-2 pr-3">{fmt(r.profit_factor)}</td>
                  <td className="py-2 pr-3">{fmt(r.max_drawdown_r)}</td>
                  <td className="py-2 pr-3">{fmt(r.rule_violations)}</td>
                  <td className="py-2 pr-3">{fmt(r.spread_slippage_acceptable)}</td>
                  <td className="py-2 pr-3">{fmt(r.small_account_feasible)}</td>
                  <td className="py-2 pr-3 font-semibold text-emerald-300">{r.promotion_readiness}</td>
                  <td className="max-w-xs py-2 pr-3 text-xs text-amber-200/90">{r.blockers.join(", ") || "—"}</td>
                  <td className="max-w-md py-2 pr-3 text-xs text-slate-400">{r.next_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-sm">
        <h3 className="mb-3 text-lg font-semibold text-emerald-400">Model promotion</h3>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] border-collapse text-left text-sm">
            <thead className="border-b border-slate-800 text-xs uppercase tracking-wide text-emerald-600">
              <tr>
                <th className="py-2 pr-3">model_key</th>
                <th className="py-2 pr-3">model_role</th>
                <th className="py-2 pr-3">status</th>
                <th className="py-2 pr-3">allowed_strategy_keys</th>
                <th className="py-2 pr-3">sample_size</th>
                <th className="py-2 pr-3">validation_score</th>
                <th className="py-2 pr-3">calibration</th>
                <th className="py-2 pr-3">pred_err_r</th>
                <th className="py-2 pr-3">readiness</th>
                <th className="py-2 pr-3">blockers</th>
                <th className="py-2 pr-3">next_action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {models.map((r) => (
                <tr key={r.model_key}>
                  <td className="py-2 pr-3 font-mono text-xs">{r.model_key}</td>
                  <td className="py-2 pr-3">{r.model_role}</td>
                  <td className="py-2 pr-3">{r.status}</td>
                  <td className="py-2 pr-3 text-xs">{r.allowed_strategy_keys.length ? r.allowed_strategy_keys.join(", ") : "—"}</td>
                  <td className="py-2 pr-3">{fmt(r.sample_size)}</td>
                  <td className="py-2 pr-3">{fmt(r.validation_score)}</td>
                  <td className="py-2 pr-3">{fmt(r.calibration_status)}</td>
                  <td className="py-2 pr-3">{fmt(r.prediction_error_r)}</td>
                  <td className="py-2 pr-3 font-semibold text-emerald-300">{r.promotion_readiness}</td>
                  <td className="max-w-xs py-2 pr-3 text-xs text-amber-200/90">{r.blockers.join(", ") || "—"}</td>
                  <td className="max-w-md py-2 pr-3 text-xs text-slate-400">{r.next_action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
