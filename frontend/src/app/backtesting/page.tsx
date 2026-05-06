"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  type BacktestExecutionCheck,
  type BacktestExecutionCheckStatus,
  type BacktestingResponse,
  type BacktestPromoteToPaperResponse,
  type BacktestRiskValidationResponse,
  type BacktestRunActionResponse,
  type BacktestSimulateExecutionResponse,
} from "@/lib/api";
import { PageHeader } from "@/components/Cards";

const EXECUTION_CHECK_LABELS: Record<string, string> = {
  simulated_entry_fill: "Simulated entry fill",
  simulated_exit_fill: "Simulated exit fill",
  spread_slippage_model: "Spread/slippage model",
  stop_loss_behavior: "Stop-loss behavior",
  target_before_stop_behavior: "Target-before-stop behavior",
  time_stop_behavior: "Time stop behavior",
  partial_fill_assumption: "Partial fill assumption",
  risk_per_trade_validation: "Risk-per-trade validation",
  max_drawdown_validation: "Max drawdown validation",
  account_survival_validation: "Account survival validation",
};

const DEFAULT_SIM_MESSAGE = "Execution simulation endpoint not connected yet.";

function defaultExecutionChecks(): BacktestExecutionCheck[] {
  return Object.keys(EXECUTION_CHECK_LABELS).map((name) => ({
    name,
    status: "not_configured" as const,
    message: DEFAULT_SIM_MESSAGE,
  }));
}

function checkStatusStyles(status: BacktestExecutionCheckStatus): string {
  switch (status) {
    case "passed":
      return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
    case "failed":
      return "border-rose-500/40 bg-rose-500/10 text-rose-200";
    case "running":
      return "border-sky-500/40 bg-sky-500/10 text-sky-200";
    case "pending":
    case "ready":
      return "border-amber-500/40 bg-amber-500/10 text-amber-200";
    case "blocked":
      return "border-orange-500/40 bg-orange-500/10 text-orange-200";
    case "not_configured":
    default:
      return "border-slate-600 bg-slate-900 text-slate-400";
  }
}

type ProfileActionKey = "run" | "simulate" | "risk" | "promote";

export default function BacktestingPage() {
  const [data, setData] = useState<BacktestingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [executionChecksByProfile, setExecutionChecksByProfile] = useState<Record<string, BacktestExecutionCheck[]>>({});
  const [lastRun, setLastRun] = useState<Record<string, BacktestRunActionResponse | null>>({});
  const [lastSim, setLastSim] = useState<Record<string, BacktestSimulateExecutionResponse | null>>({});
  const [lastRisk, setLastRisk] = useState<Record<string, BacktestRiskValidationResponse | null>>({});
  const [lastPromote, setLastPromote] = useState<Record<string, BacktestPromoteToPaperResponse | null>>({});
  const [loading, setLoading] = useState<Record<string, Partial<Record<ProfileActionKey, boolean>>>>({});

  useEffect(() => {
    api
      .getBacktestingSummary()
      .then(setData)
      .catch(() => setError("Backtesting endpoint not connected yet."));
  }, []);

  useEffect(() => {
    if (!data?.profiles?.length) return;
    setExecutionChecksByProfile((prev) => {
      const next = { ...prev };
      for (const p of data.profiles) {
        if (!next[p.profile_name]) next[p.profile_name] = defaultExecutionChecks();
      }
      return next;
    });
  }, [data]);

  const setBusy = useCallback((profile: string, key: ProfileActionKey, v: boolean) => {
    setLoading((prev) => ({
      ...prev,
      [profile]: { ...prev[profile], [key]: v },
    }));
  }, []);

  const handleRun = async (profileName: string) => {
    setBusy(profileName, "run", true);
    try {
      const res = await api.postBacktestingRun({ profile_name: profileName });
      setLastRun((p) => ({ ...p, [profileName]: res }));
    } catch {
      setLastRun((p) => ({
        ...p,
        [profileName]: {
          status: "not_configured",
          message: DEFAULT_SIM_MESSAGE,
          profile_name: profileName,
        },
      }));
    } finally {
      setBusy(profileName, "run", false);
    }
  };

  const handleSimulate = async (profileName: string) => {
    setBusy(profileName, "simulate", true);
    try {
      const res = await api.postBacktestingSimulateExecution({ profile_name: profileName });
      setLastSim((p) => ({ ...p, [profileName]: res }));
      if (res.checks?.length) {
        setExecutionChecksByProfile((p) => ({ ...p, [profileName]: res.checks }));
      }
    } catch {
      setExecutionChecksByProfile((p) => ({ ...p, [profileName]: defaultExecutionChecks() }));
      setLastSim((p) => ({
        ...p,
        [profileName]: {
          status: "not_configured",
          message: DEFAULT_SIM_MESSAGE,
          profile_name: profileName,
          checks: defaultExecutionChecks(),
        },
      }));
    } finally {
      setBusy(profileName, "simulate", false);
    }
  };

  const handleRisk = async (profileName: string) => {
    setBusy(profileName, "risk", true);
    try {
      const res = await api.postBacktestingValidateRisk({ profile_name: profileName });
      setLastRisk((p) => ({ ...p, [profileName]: res }));
    } catch {
      setLastRisk((p) => ({
        ...p,
        [profileName]: {
          status: "not_configured",
          message: DEFAULT_SIM_MESSAGE,
          profile_name: profileName,
          checks: [],
        },
      }));
    } finally {
      setBusy(profileName, "risk", false);
    }
  };

  const handlePromote = async (profileName: string) => {
    setBusy(profileName, "promote", true);
    try {
      const res = await api.postBacktestingPromoteToPaper({ profile_name: profileName });
      setLastPromote((p) => ({ ...p, [profileName]: res }));
    } catch {
      setLastPromote((p) => ({
        ...p,
        [profileName]: {
          status: "not_configured",
          message: DEFAULT_SIM_MESSAGE,
          profile_name: profileName,
          blocked_reasons: [],
        },
      }));
    } finally {
      setBusy(profileName, "promote", false);
    }
  };

  const actionBtn =
    "rounded-lg border border-slate-600 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-200 transition hover:border-emerald-500/40 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50";

  const profiles = useMemo(() => data?.profiles ?? [], [data]);

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="model validation"
          title="Backtesting"
          description="Backtesting validates whether signals actually work for small accounts. The objective is not accuracy. It is expectancy, target-before-stop behavior, drawdown control, and account survivability."
        />

        <div className="mb-4 rounded-xl border border-sky-500/30 bg-sky-950/40 px-4 py-3 text-sm leading-relaxed text-sky-100/95">
          <strong className="text-sky-200">Simulated execution only.</strong> Backtesting uses simulated historical execution
          only. Paper or live orders are handled in <span className="text-emerald-300">Paper Trading</span> and{" "}
          <span className="text-emerald-300">TradeNow</span> after risk approval. No broker orders are submitted from this
          page.
        </div>

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading backtesting plan...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-emerald-500">Mode</p>
              <h2 className="mt-2 text-3xl font-semibold text-white">{data.mode.replace(/_/g, " ")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">
                Backtest profiles define how the platform will prove that recommendations are actionable and not just attractive-looking signals.
              </p>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {profiles.map((profile) => {
                const checks = executionChecksByProfile[profile.profile_name] ?? defaultExecutionChecks();
                const busy = loading[profile.profile_name] ?? {};

                return (
                  <article key={profile.profile_name} className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-emerald-500">{profile.horizon}</p>
                        <h2 className="mt-1 text-2xl font-semibold text-white">{profile.profile_name}</h2>
                      </div>
                      <span className="w-fit rounded-full border border-amber-500 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase text-amber-300">
                        {profile.status.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2 text-xs text-slate-300">
                      <span className="font-semibold uppercase tracking-wide text-slate-500">Promotion gate</span>
                      <p className="mt-1 font-mono text-sm text-emerald-300">{profile.promotion_gate ?? "contract_ready"}</p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        contract_ready → data_ready → backtest_running → backtest_passed → execution_sim_passed →
                        risk_validated → paper_ready (or blocked)
                      </p>
                    </div>

                    <p className="mt-3 text-sm leading-relaxed text-slate-300">{profile.objective}</p>

                    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                      {profile.metrics.map((metric) => (
                        <div key={metric.name} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                          <p className="text-xs uppercase tracking-wide text-slate-500">{metric.name}</p>
                          <p className="mt-1 text-lg font-semibold text-white">{metric.value}</p>
                          <p className="mt-1 text-xs text-slate-400">{metric.status}</p>
                        </div>
                      ))}
                    </div>

                    <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-3">
                      <h3 className="text-sm font-semibold text-emerald-500">Next Steps</h3>
                      <ul className="mt-2 space-y-2 text-sm leading-relaxed text-slate-300">
                        {profile.next_steps.map((step) => (
                          <li key={step}>• {step}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="mt-4 rounded-lg border border-sky-800/60 bg-slate-900/90 p-3">
                      <h3 className="text-sm font-semibold text-sky-400">Execution Simulation</h3>
                      <p className="mt-1 text-xs text-slate-500">
                        Validates simulated fills, friction model, exit logic, and risk caps. Does not place orders.
                      </p>
                      <ul className="mt-3 space-y-2">
                        {checks.map((c) => (
                          <li
                            key={c.name}
                            className={`flex flex-col gap-1 rounded-md border px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between ${checkStatusStyles(c.status)}`}
                          >
                            <span className="font-medium text-slate-100">{EXECUTION_CHECK_LABELS[c.name] ?? c.name}</span>
                            <span className="font-mono uppercase">{c.status}</span>
                            {c.message ? <p className="mt-1 w-full text-[11px] opacity-90 sm:mt-0">{c.message}</p> : null}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                      <button type="button" className={actionBtn} disabled={busy.run} onClick={() => void handleRun(profile.profile_name)}>
                        {busy.run ? "Running…" : "Run Backtest"}
                      </button>
                      <button
                        type="button"
                        className={actionBtn}
                        disabled={busy.simulate}
                        onClick={() => void handleSimulate(profile.profile_name)}
                      >
                        {busy.simulate ? "Running…" : "Run Simulated Execution"}
                      </button>
                      <button type="button" className={actionBtn} disabled={busy.risk} onClick={() => void handleRisk(profile.profile_name)}>
                        {busy.risk ? "Running…" : "Run Risk Validation"}
                      </button>
                      <button
                        type="button"
                        className={actionBtn}
                        disabled={busy.promote}
                        onClick={() => void handlePromote(profile.profile_name)}
                      >
                        {busy.promote ? "Working…" : "Promote to Paper Trading"}
                      </button>
                    </div>

                    <div className="mt-3 space-y-2 rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-[11px] text-slate-400">
                      {lastRun[profile.profile_name] ? (
                        <p>
                          <span className="text-slate-500">Run Backtest:</span> {lastRun[profile.profile_name]?.status} —{" "}
                          {lastRun[profile.profile_name]?.message}
                        </p>
                      ) : null}
                      {lastSim[profile.profile_name] ? (
                        <p>
                          <span className="text-slate-500">Simulated execution:</span> {lastSim[profile.profile_name]?.status} —{" "}
                          {lastSim[profile.profile_name]?.message}
                        </p>
                      ) : null}
                      {lastRisk[profile.profile_name] ? (
                        <p>
                          <span className="text-slate-500">Risk validation:</span> {lastRisk[profile.profile_name]?.status} —{" "}
                          {lastRisk[profile.profile_name]?.message}
                        </p>
                      ) : null}
                      {lastPromote[profile.profile_name] ? (
                        <p>
                          <span className="text-slate-500">Promote:</span> {lastPromote[profile.profile_name]?.status} —{" "}
                          {lastPromote[profile.profile_name]?.message}
                          {lastPromote[profile.profile_name]?.blocked_reasons?.length
                            ? ` (${lastPromote[profile.profile_name]!.blocked_reasons!.join(", ")})`
                            : ""}
                        </p>
                      ) : null}
                    </div>
                  </article>
                );
              })}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
