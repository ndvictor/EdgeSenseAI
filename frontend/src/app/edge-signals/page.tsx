"use client";

import { FormEvent, useEffect, useState } from "react";
import { api, type EdgeSignal, type EdgeSignalRule, type MarketScannerResponse, type MarketScanRun, type StrategyConfig, type StrategyWorkflowRunResult } from "@/lib/api";
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
  const [triggerWorkflow, setTriggerWorkflow] = useState(false);
  const [scanResult, setScanResult] = useState<MarketScannerResponse | null>(null);
  const [scanRuns, setScanRuns] = useState<MarketScanRun[]>([]);
  const [latestScanRun, setLatestScanRun] = useState<MarketScanRun | null>(null);
  const [latestWorkflowRun, setLatestWorkflowRun] = useState<StrategyWorkflowRunResult | null>(null);
  const [runLogError, setRunLogError] = useState<string | null>(null);
  const [scheduledLoading, setScheduledLoading] = useState(false);

  useEffect(() => {
    Promise.all([api.getEdgeSignals(), api.getStrategies(), api.getEdgeSignalRules(), api.getMarketScanRuns(), api.getLatestMarketScanRun(), api.getLatestStrategyWorkflowRun()])
      .then(([data, strategiesData, rulesData, runsData, latestRunData, latestWorkflowData]) => {
        setSignals(data.signals);
        setLastUpdated(data.last_updated);
        setStrategies(strategiesData);
        setRules(rulesData);
        setScanRuns(runsData);
        setLatestScanRun(latestRunData);
        setLatestWorkflowRun(latestWorkflowData);
        if (strategiesData[0]?.strategy_key) setStrategyKey(strategiesData[0].strategy_key);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function refreshScanRuns() {
    setRunLogError(null);
    try {
      const [runsData, latestRunData, latestWorkflowData] = await Promise.all([api.getMarketScanRuns(), api.getLatestMarketScanRun(), api.getLatestStrategyWorkflowRun()]);
      setScanRuns(runsData);
      setLatestScanRun(latestRunData);
      setLatestWorkflowRun(latestWorkflowData);
    } catch (err) {
      setRunLogError(err instanceof Error ? err.message : "Unable to load scan run history");
    }
  }

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
        trigger_workflow: triggerWorkflow,
        account_size: accountSize,
        max_risk_per_trade: maxRisk,
      });
      setScanResult(response);
      await refreshScanRuns();
    } catch (err) {
      setScannerError(err instanceof Error ? err.message : "Market scanner failed");
    } finally {
      setScannerLoading(false);
    }
  }

  async function runScheduledOnce() {
    setScheduledLoading(true);
    setRunLogError(null);
    try {
      await api.runScheduledMarketScanOnce();
      await refreshScanRuns();
    } catch (err) {
      setRunLogError(err instanceof Error ? err.message : "Scheduled scan test failed");
    } finally {
      setScheduledLoading(false);
    }
  }

  const highUrgency = signals.filter((signal) => signal.urgency === "high" || signal.urgency === "critical").length;
  const fullyValidated = signals.filter((signal) => signal.spread_pass && signal.liquidity_pass && signal.regime_pass).length;
  const reviewNeeded = signals.length - fullyValidated;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
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
            <label className="flex items-center gap-3 self-end text-sm font-semibold text-slate-300">
              <input type="checkbox" checked={triggerWorkflow} onChange={(event) => setTriggerWorkflow(event.target.checked)} />
              trigger paper workflow
            </label>
            <button disabled={scannerLoading} className="self-end rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-300 disabled:opacity-60">
              {scannerLoading ? "Scanning..." : "Scan Market Conditions"}
            </button>
          </form>

          {!scanResult ? <div className="mt-4"><EmptyState label="market scanner results" /></div> : (
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
                <MetricCard label="Strategy" value={scanResult.strategy_key} accent />
                <MetricCard label="Run ID" value={scanResult.run_id.slice(0, 8)} />
                <MetricCard label="Symbols" value={scanResult.symbols_scanned.length} />
                <MetricCard label="Matched" value={scanResult.matched_signals.length} />
                <MetricCard label="Skipped" value={scanResult.skipped_signals.length} />
                <MetricCard label="Trigger Workflow" value={scanResult.should_trigger_workflow ? "Yes" : "No"} />
                <MetricCard label="Data Source" value={scanResult.data_source} />
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={scanResult.recommended_workflow_key} />
                  <Badge value={scanResult.workflow_trigger_status} />
                  {scanResult.workflow_run_id && <Badge value={scanResult.workflow_run_id} />}
                  {scanResult.cooldown_remaining_seconds !== null && scanResult.cooldown_remaining_seconds !== undefined && <Badge value={`${scanResult.cooldown_remaining_seconds}s cooldown`} />}
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

        <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
          <h2 className="mb-3 text-lg font-semibold text-emerald-500">Latest Strategy Workflow Run</h2>
          {!latestWorkflowRun ? <EmptyState label="strategy workflow run" /> : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
                <MetricCard label="Workflow Run" value={latestWorkflowRun.workflow_run_id.slice(0, 12)} accent />
                <MetricCard label="Strategy" value={latestWorkflowRun.strategy_key} />
                <MetricCard label="Symbol" value={latestWorkflowRun.symbol} />
                <MetricCard label="Signal" value={latestWorkflowRun.matched_signal_name || latestWorkflowRun.matched_signal_key || "manual"} />
                <MetricCard label="Status" value={latestWorkflowRun.status} />
                <MetricCard label="Live Allowed" value={latestWorkflowRun.live_trading_allowed ? "Yes" : "No"} />
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={latestWorkflowRun.approval_required ? "approval_required" : "approval_not_required"} />
                  <Badge value={latestWorkflowRun.paper_trade_allowed ? "paper_allowed" : "paper_not_allowed"} />
                  <Badge value={String(latestWorkflowRun.recommendation?.action || "watch_only")} />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{String(latestWorkflowRun.recommendation?.next_action || "Review workflow result before any paper action.")}</p>
              </div>
            </div>
          )}
        </section>

        <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-lg font-semibold text-emerald-500">Scheduled Scan Runs</h2>
              <p className="mt-1 text-sm text-slate-300">Scheduler visibility for scan-and-alert runs only. Live trading is disabled and human approval remains required.</p>
            </div>
            <button onClick={runScheduledOnce} disabled={scheduledLoading} className="rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-300 disabled:opacity-60">
              {scheduledLoading ? "Running..." : "Run Scheduled Scan Once"}
            </button>
          </div>
          {runLogError && <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{runLogError}</div>}
          <div className="mt-4">
            {!latestScanRun ? <EmptyState label="latest scan run" /> : (
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
                <MetricCard label="Latest Run" value={latestScanRun.run_id.slice(0, 8)} accent />
                <MetricCard label="Trigger" value={latestScanRun.trigger_type} />
                <MetricCard label="Strategy" value={latestScanRun.strategy_key} />
                <MetricCard label="Matched" value={latestScanRun.matched_signals_count} />
                <MetricCard label="Skipped" value={latestScanRun.skipped_signals_count} />
                <MetricCard label="Status" value={latestScanRun.status} />
              </div>
            )}
            {latestScanRun && (
              <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4">
                <div className="flex flex-wrap gap-2">
                  <Badge value={latestScanRun.data_source} />
                  <Badge value={latestScanRun.should_trigger_workflow ? "workflow_trigger_ready" : "workflow_not_triggered"} />
                  <Badge value={latestScanRun.workflow_trigger_status} />
                  {latestScanRun.cooldown_remaining_seconds !== null && latestScanRun.cooldown_remaining_seconds !== undefined && <Badge value={`${latestScanRun.cooldown_remaining_seconds}s cooldown`} />}
                  <Badge value={latestScanRun.auto_run_enabled ? "auto_run_enabled" : "auto_run_disabled"} />
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{latestScanRun.next_action}</p>
                <p className="mt-2 text-sm text-slate-400">Symbols: {latestScanRun.symbols.join(", ")} · Workflow: {latestScanRun.recommended_workflow_key}</p>
              </div>
            )}
          </div>
          <div className="mt-4">
            <ScanRunsTable runs={scanRuns} />
          </div>
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

function ScanRunsTable({ runs }: { runs: MarketScanRun[] }) {
  if (!runs.length) return <EmptyState label="recent scan runs" />;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full min-w-[1240px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr>
            <th className="px-4 py-3">Run ID</th>
            <th className="px-4 py-3">Trigger</th>
            <th className="px-4 py-3">Strategy</th>
            <th className="px-4 py-3">Symbols</th>
            <th className="px-4 py-3">Matched</th>
            <th className="px-4 py-3">Skipped</th>
            <th className="px-4 py-3">Trigger Workflow</th>
            <th className="px-4 py-3">Next Action</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Started</th>
            <th className="px-4 py-3">Completed</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {runs.map((run) => (
            <tr key={run.run_id}>
              <td className="px-4 py-3 font-mono text-xs text-white">{run.run_id.slice(0, 8)}</td>
              <td className="px-4 py-3"><Badge value={run.trigger_type} /></td>
              <td className="px-4 py-3 text-slate-300">{run.strategy_key}</td>
              <td className="max-w-xs px-4 py-3 text-slate-300">{run.symbols.join(", ")}</td>
              <td className="px-4 py-3 text-slate-300">{run.matched_signals_count}</td>
              <td className="px-4 py-3 text-slate-300">{run.skipped_signals_count}</td>
              <td className="px-4 py-3"><Badge value={run.should_trigger_workflow ? "yes" : "no"} /></td>
              <td className="max-w-md px-4 py-3 text-slate-400">{run.next_action}{run.cooldown_remaining_seconds ? ` Cooldown: ${run.cooldown_remaining_seconds}s.` : ""}</td>
              <td className="px-4 py-3"><Badge value={run.status} /></td>
              <td className="px-4 py-3 text-slate-300">{run.started_at ? new Date(run.started_at).toLocaleString() : "N/A"}</td>
              <td className="px-4 py-3 text-slate-300">{run.completed_at ? new Date(run.completed_at).toLocaleString() : "N/A"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
