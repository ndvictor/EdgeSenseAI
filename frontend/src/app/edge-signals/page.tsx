"use client";

import { useEffect, useState } from "react";
import { api, type EdgeSignal } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

function passLabel(value: boolean) {
  return value ? "PASS" : "REVIEW";
}

function passClass(value: boolean) {
  return value ? "border-emerald-500 bg-emerald-500/10 text-emerald-300" : "border-amber-500 bg-amber-500/10 text-amber-300";
}

export default function EdgeSignalsPage() {
  const [signals, setSignals] = useState<EdgeSignal[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getEdgeSignals()
      .then((data) => {
        setSignals(data.signals);
        setLastUpdated(data.last_updated);
      })
      .catch((err) => setError(err.message));
  }, []);

  const highUrgency = signals.filter((signal) => signal.urgency === "high" || signal.urgency === "critical").length;
  const fullyValidated = signals.filter((signal) => signal.spread_pass && signal.liquidity_pass && signal.regime_pass).length;
  const reviewNeeded = signals.length - fullyValidated;

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px] space-y-4">
        <PageHeader
          eyebrow="urgent edge validation"
          title="Edge Signals"
          description="Fast signals are not recommendations by themselves. They must pass spread, liquidity, regime, and account-fit gates before they can be promoted into a top action."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
        <div className="text-sm text-slate-800">Last updated: {lastUpdated ? new Date(lastUpdated).toLocaleString() : "loading"}</div>

        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard label="Signals" value={signals.length} accent />
          <MetricCard label="High urgency" value={highUrgency} />
          <MetricCard label="Fully validated" value={fullyValidated} />
          <MetricCard label="Needs review" value={reviewNeeded} />
        </div>

        <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-emerald-500">Validation Gates</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Spread Gate</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">Reject signals where bid/ask spread makes the trade too expensive for a small account.</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Liquidity Gate</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">Avoid traps where the signal looks strong but volume or depth is too weak.</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Regime Gate</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">Only promote signals that fit the current risk-on, risk-off, trend, or chop regime.</p>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Account Gate</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">Route expensive opportunities to fractional, defined-risk, or watch-only expressions.</p>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          {signals.map((signal) => (
            <article key={`${signal.symbol}-${signal.signal_type}`} className="rounded-xl border border-slate-800 bg-slate-950 p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-emerald-500">{signal.signal_name}</p>
                  <h2 className="mt-1 text-3xl font-black text-white">{signal.symbol}</h2>
                  <p className="mt-1 text-sm uppercase text-slate-400">{signal.asset_class} · {signal.time_decay}</p>
                </div>
                <span className="rounded-full border border-violet-500 bg-violet-500/10 px-3 py-1 text-xs font-bold uppercase text-violet-300">{signal.urgency}</span>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Edge Score</p>
                  <p className="mt-1 text-2xl font-black text-emerald-500">{signal.edge_score}</p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Confidence</p>
                  <p className="mt-1 text-2xl font-black text-emerald-500">{Math.round(signal.confidence * 100)}%</p>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-bold uppercase">
                <span className={`rounded-full border px-3 py-2 text-center ${passClass(signal.spread_pass)}`}>Spread {passLabel(signal.spread_pass)}</span>
                <span className={`rounded-full border px-3 py-2 text-center ${passClass(signal.liquidity_pass)}`}>Liquidity {passLabel(signal.liquidity_pass)}</span>
                <span className={`rounded-full border px-3 py-2 text-center ${passClass(signal.regime_pass)}`}>Regime {passLabel(signal.regime_pass)}</span>
                <span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-3 py-2 text-center text-cyan-300">{signal.account_fit.replace(/_/g, " ")}</span>
              </div>

              <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-3">
                <p className="text-xs uppercase tracking-wide text-slate-500">Action</p>
                <p className="mt-1 text-sm leading-relaxed text-slate-300">{signal.recommended_action}</p>
              </div>

              <p className="mt-3 text-sm leading-relaxed text-slate-400">{signal.reason}</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {signal.risk_factors.map((risk) => (
                  <span key={risk} className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs text-amber-300">{risk}</span>
                ))}
              </div>
            </article>
          ))}
        </section>
      </div>
    </div>
  );
}
