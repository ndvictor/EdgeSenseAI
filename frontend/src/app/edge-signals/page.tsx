"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, type EdgeSignal, type EdgeSignalRule, type MarketScannerResponse, type StrategyConfig } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

function passLabel(value: boolean) {
  return value ? "PASS" : "REVIEW";
}

function passClass(value: boolean) {
  return value ? "border-emerald-500 bg-emerald-500/10 text-emerald-300" : "border-amber-500 bg-amber-500/10 text-amber-300";
}

function badgeClass(value?: string | boolean | null) {
  const text = String(value ?? "unknown").toLowerCase();
  if (text.includes("matched") || text.includes("enabled") || text.includes("source_backed")) return "border-emerald-500 bg-emerald-500/10 text-emerald-300";
  if (text.includes("placeholder") || text.includes("skipped") || text.includes("warn") || text.includes("demo")) return "border-amber-500 bg-amber-500/10 text-amber-300";
  if (text.includes("fail") || text.includes("disabled")) return "border-rose-500 bg-rose-500/10 text-rose-300";
  return "border-slate-600 bg-slate-800 text-slate-300";
}

function Badge({ value }: { value?: string | boolean | null }) {
  const label = value === true ? "true" : value === false ? "false" : value || "unknown";
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${badgeClass(value)}`}>{String(label).replace(/_/g, " ")}</span>;
}

function EmptyState({ label }: { label: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-6 text-center text-sm text-slate-400">No {label} available yet.</div>;
}

export default function EdgeSignalsPage() {
  const [signals, setSignals] = useState<EdgeSignal[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [rules, setRules] = useState<EdgeSignalRule[]>([]);
  const [scannerError, setScannerError] = useState<string | null>(null);
  const [scannerLoading, setScannerLoading] = useState(false);
  const [strategyKey, setStrategyKey] = useState("stock_day_trading");
  const [scannerSymbols, setScannerSymbols] = useState("AMD,NVDA,AAPL,MSFT,BTC-USD");
  const [scannerSource, setScannerSource] = useState("auto");
  const [accountSize, setAccountSize] = useState(5000);
  const [maxRisk, setMaxRisk] = useState(0.01);
  const [autoRun, setAutoRun] = useState(false);
  const [scanResult, setScanResult] = useState<MarketScannerResponse | null>(null);

  useEffect(() => {
    Promise.all([api.getEdgeSignals(), api.getStrategies(), api.getEdgeSignalRules()])
      .then(([data, strategiesData, rulesData]) => {
        setSignals(data.signals);
        setLastUpdated(data.last_updated);
        setStrategies(strategiesData);
        setRules(rulesData);
        if (strategiesData[0]?.strategy_key) setStrategyKey(strategiesData[0].strategy_key);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function runScanner(event: FormEvent) {
    event.preventDefault();
    setScannerLoading(true);
    setScannerError(null);
    try {
      const response = await api.scanMarketConditions({
        strategy_key: strategyKey,
        symbols: scannerSymbols.split(",").map((symbol) => symbol.trim()).filter(Boolean),
        data_source: scannerSource,
        auto_run: autoRun,
        account_size: accountSize,
        max_risk_per_trade: maxRisk,
      });
      setScanResult(response);
    } catch (err) {
      setScannerError(err instanceof Error ? err.message : "Market scanner failed");
    } finally {
      setScannerLoading(false);
    }
  }

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

        <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-emerald-500">Market Scanner</h2>
          <p className="mb-4 text-sm text-slate-300">Paper/research-only scanner. Auto-run can request workflow triggering, but human approval remains required and live trading stays disabled.</p>
          {scannerError && <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{scannerError}</div>}
          <form onSubmit={runScanner} className="grid grid-cols-1 gap-3 lg:grid-cols-6">
            <label className="lg:col-span-2">
              <span className="text-xs uppercase tracking-wide text-slate-400">Strategy</span>
              <select value={strategyKey} onChange={(event) => setStrategyKey(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white">
                {strategies.map((strategy) => <option key={strategy.strategy_key} value={strategy.strategy_key}>{strategy.display_name}</option>)}
              </select>
            </label>
            <label className="lg:col-span-2">
              <span className="text-xs uppercase tracking-wide text-slate-400">Symbols</span>
              <input value={scannerSymbols} onChange={(event) => setScannerSymbols(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
            </label>
            <label>
              <span className="text-xs uppercase tracking-wide text-slate-400">Data Source</span>
              <select value={scannerSource} onChange={(event) => setScannerSource(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white">
                {["auto", "yfinance", "mock"].map((source) => <option key={source}>{source}</option>)}
              </select>
            </label>
            <label>
              <span className="text-xs uppercase tracking-wide text-slate-400">Account Size</span>
              <input type="number" value={accountSize} onChange={(event) => setAccountSize(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
            </label>
            <label>
              <span className="text-xs uppercase tracking-wide text-slate-400">Risk / Trade</span>
              <input type="number" step="0.01" value={maxRisk} onChange={(event) => setMaxRisk(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
            </label>
            <label className="flex items-center gap-3 self-end text-sm font-semibold text-slate-300">
              <input type="checkbox" checked={autoRun} onChange={(event) => setAutoRun(event.target.checked)} />
              auto-run request
            </label>
            <button disabled={scannerLoading} className="self-end rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-300 disabled:opacity-60">
              {scannerLoading ? "Scanning..." : "Scan Market Conditions"}
            </button>
          </form>

          {!scanResult ? <div className="mt-4"><EmptyState label="market scanner results" /></div> : (
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
                <MetricCard label="Strategy" value={scanResult.strategy_key} accent />
                <MetricCard label="Symbols" value={scanResult.symbols_scanned.length} />
                <MetricCard label="Matched" value={scanResult.matched_signals.length} />
                <MetricCard label="Skipped" value={scanResult.skipped_signals.length} />
                <MetricCard label="Trigger Workflow" value={scanResult.should_trigger_workflow ? "Yes" : "No"} />
                <MetricCard label="Data Source" value={scanResult.data_source} />
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={scanResult.recommended_workflow_key} />
                  <Badge value={scanResult.safety_state.auto_run_enabled ? "auto_run_on" : "auto_run_off"} />
                  <Badge value={scanResult.safety_state.live_trading_enabled ? "live_enabled" : "live_disabled"} />
                  <Badge value={scanResult.safety_state.require_human_approval ? "human_approval_required" : "approval_not_required"} />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{scanResult.next_action}</p>
                <p className="mt-2 text-sm text-slate-400">Required agents: {scanResult.required_agents.join(", ") || "none"} · Required models: {scanResult.required_models.join(", ") || "none"}</p>
              </div>
              <ScannerTable title="Matched Signals" rows={scanResult.matched_signals} />
              <ScannerTable title="Skipped Signals" rows={scanResult.skipped_signals} />
            </div>
          )}
        </section>

        <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-emerald-500">Edge Signal Rules</h2>
          {!rules.length ? <EmptyState label="edge signal rules" /> : (
            <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
              <table className="w-full min-w-[1180px] text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-emerald-600">
                  <tr><th className="px-4 py-3">Signal</th><th className="px-4 py-3">Asset Classes</th><th className="px-4 py-3">Timeframes</th><th className="px-4 py-3">Required Metrics</th><th className="px-4 py-3">Interval</th><th className="px-4 py-3">Enabled</th><th className="px-4 py-3">Uses LLM</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {rules.map((rule) => (
                    <tr key={rule.signal_key}>
                      <td className="px-4 py-3"><p className="font-bold text-white">{rule.display_name}</p><p className="mt-1 max-w-md text-xs text-slate-400">{rule.signal_to_look_for}</p></td>
                      <td className="px-4 py-3 text-slate-300">{rule.supported_asset_classes.join(", ")}</td>
                      <td className="px-4 py-3 text-slate-300">{rule.supported_timeframes.join(", ")}</td>
                      <td className="max-w-md px-4 py-3 text-slate-300">{rule.required_metrics.join(", ")}</td>
                      <td className="px-4 py-3 text-slate-300">{rule.scan_interval_seconds}s</td>
                      <td className="px-4 py-3"><Badge value={rule.enabled_by_default} /></td>
                      <td className="px-4 py-3"><Badge value={rule.uses_llm ? "uses_llm" : "deterministic"} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function ScannerTable({ title, rows }: { title: string; rows: MarketScannerResponse["matched_signals"] }) {
  if (!rows.length) return <EmptyState label={title.toLowerCase()} />;
  return (
    <div>
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-emerald-500">{title}</h3>
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-emerald-600">
            <tr><th className="px-4 py-3">Symbol</th><th className="px-4 py-3">Signal</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Strength</th><th className="px-4 py-3">Validation</th><th className="px-4 py-3">Reason</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {rows.map((row, index) => (
              <tr key={`${row.symbol}-${row.signal_key}-${index}`}>
                <td className="px-4 py-3 font-bold text-white">{row.symbol}</td>
                <td className="px-4 py-3 text-slate-300">{row.display_name}</td>
                <td className="px-4 py-3"><Badge value={row.status} /></td>
                <td className="px-4 py-3 text-slate-300">{row.confidence !== null && row.confidence !== undefined ? `${Math.round(row.confidence * 100)}%` : "N/A"}</td>
                <td className="px-4 py-3"><Badge value={row.data_source} /></td>
                <td className="max-w-xl px-4 py-3 text-slate-400">{row.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
