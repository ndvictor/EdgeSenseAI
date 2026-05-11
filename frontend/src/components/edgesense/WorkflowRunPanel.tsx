"use client";

import { useMemo, useState } from "react";

import type { TradingGatesResponse } from "@/components/edgesense/GateSettingsPanel";

type RunMode = "plan_only" | "paper" | "live";

type RunResult = {
  status?: string;
  run_mode?: string;
  submitted_order?: boolean;
  broker_called?: boolean;
  reason?: string;
  detail?: unknown;
};

export function WorkflowRunPanel({ gates }: { gates: TradingGatesResponse | null }) {
  const [mode, setMode] = useState<RunMode>("plan_only");
  const [symbols, setSymbols] = useState("");
  const [confirmLive, setConfirmLive] = useState(false);
  const [phrase, setPhrase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);

  const opsConfigured = gates?.context.ops_admin_token_configured ?? false;
  const paperAllowed = gates?.context.paper_run_allowed ?? false;
  const liveAllowed = gates?.context.live_run_allowed ?? false;
  const livePhraseOk = phrase.trim() === "LIVE";
  const canSubmit = useMemo(() => {
    if (busy || !opsConfigured) return false;
    if (mode === "plan_only") return true;
    if (mode === "paper") return paperAllowed;
    return liveAllowed && confirmLive && livePhraseOk;
  }, [busy, opsConfigured, mode, paperAllowed, liveAllowed, confirmLive, livePhraseOk]);

  async function runWorkflow() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const response = await fetch("/api/edgesense/workflow-run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_mode: mode,
          symbols: symbols
            .split(",")
            .map((symbol) => symbol.trim().toUpperCase())
            .filter(Boolean),
          confirm_live: mode === "live" ? confirmLive : false,
          confirm_live_phrase: mode === "live" ? phrase.trim() : null,
        }),
      });
      const body = (await response.json().catch(() => ({}))) as RunResult;
      if (!response.ok) {
        const detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body.reason || body);
        setError(`Run rejected: ${detail}`);
        return;
      }
      setResult(body);
    } catch {
      setError("Run failed: network error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      id="run"
      className="mb-6 scroll-mt-6 rounded-3xl border border-white/8 bg-[#04111a]/85 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.42)] backdrop-blur"
    >
      <header className="mb-4">
        <h2 className="text-base font-black uppercase tracking-[0.12em] text-cyan-50">Run Workflow</h2>
        <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
          Start DeepAgents now. Plan-only never submits orders. Paper uses the simulator. Live is real broker execution and requires explicit confirmation.
        </p>
      </header>

      {!opsConfigured ? (
        <div className="mb-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          Protected RUN is disabled because OPS_ADMIN_TOKEN is not configured for the frontend/backend proxy.
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
          <div className="mb-3 text-[11px] font-black uppercase tracking-[0.16em] text-cyan-50">Mode</div>
          <ModeButton active={mode === "plan_only"} label="Plan only" desc="Reasoning + planning only; no orders." onClick={() => setMode("plan_only")} />
          <ModeButton active={mode === "paper"} disabled={!paperAllowed} label="Run paper workflow" desc={paperAllowed ? "Paper simulator; broker_called=false." : "Blocked by paper gates."} onClick={() => setMode("paper")} />
          <ModeButton active={mode === "live"} disabled={!liveAllowed} danger label="Run live workflow" desc={liveAllowed ? "Real broker; requires confirmation." : "Blocked until live gates allow it."} onClick={() => setMode("live")} />

          <label className="mt-4 block text-xs text-slate-400">
            <span className="mb-1 block uppercase tracking-[0.14em] text-slate-500">Symbols (optional)</span>
            <input
              value={symbols}
              onChange={(event) => setSymbols(event.target.value)}
              placeholder="AAPL, MSFT, NVDA"
              className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-xs text-slate-100 placeholder:text-slate-600 focus:border-cyan-300/40 focus:outline-none"
            />
          </label>
        </div>

        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-4">
          <div className="mb-3 text-[11px] font-black uppercase tracking-[0.16em] text-cyan-50">Confirm</div>
          {mode === "live" ? (
            <div className="space-y-3">
              <label className="flex items-start gap-2 rounded-xl border border-rose-400/25 bg-rose-500/[0.06] p-3 text-xs text-rose-100">
                <input type="checkbox" checked={confirmLive} onChange={(event) => setConfirmLive(event.target.checked)} />
                <span>I understand this can submit real orders through the broker adapter.</span>
              </label>
              <label className="block text-xs text-rose-100">
                Type LIVE
                <input
                  value={phrase}
                  onChange={(event) => setPhrase(event.target.value)}
                  placeholder="LIVE"
                  className="mt-1 w-full rounded-lg border border-rose-400/30 bg-black/40 px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none"
                />
              </label>
            </div>
          ) : (
            <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3 text-xs text-slate-400">
              No live confirmation is required for this mode.
            </div>
          )}

          <button
            type="button"
            onClick={runWorkflow}
            disabled={!canSubmit}
            className={`mt-4 w-full rounded-lg border px-4 py-2.5 text-sm font-black uppercase tracking-[0.16em] transition disabled:opacity-50 ${
              mode === "live"
                ? "border-rose-400/40 bg-rose-500/15 text-rose-100"
                : mode === "paper"
                  ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100"
                  : "border-cyan-400/30 bg-cyan-400/10 text-cyan-100"
            }`}
          >
            {busy ? "Running…" : `Run · ${mode.replace("_", " ")}`}
          </button>
          {error ? <div className="mt-3 rounded-xl border border-rose-400/30 bg-rose-500/10 p-3 text-xs text-rose-100">{error}</div> : null}
        </div>
      </div>

      {result ? (
        <div className="mt-4 grid gap-2 rounded-2xl border border-white/8 bg-white/[0.02] p-4 text-xs md:grid-cols-4">
          <Fact label="status" value={result.status ?? "—"} />
          <Fact label="run_mode" value={result.run_mode ?? mode} />
          <Fact label="submitted_order" value={fmtBool(result.submitted_order)} />
          <Fact label="broker_called" value={fmtBool(result.broker_called)} tone={result.broker_called ? "rose" : "emerald"} />
        </div>
      ) : null}
    </section>
  );
}

function ModeButton({ active, disabled, danger, label, desc, onClick }: { active: boolean; disabled?: boolean; danger?: boolean; label: string; desc: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={`mb-2 w-full rounded-xl border px-3 py-2.5 text-left transition disabled:cursor-not-allowed disabled:opacity-50 ${
        active ? (danger ? "border-rose-400/40 bg-rose-500/[0.08]" : "border-cyan-300/40 bg-cyan-400/10") : "border-white/8 bg-white/[0.02] hover:bg-white/[0.04]"
      }`}
    >
      <div className="font-mono text-xs font-bold text-slate-100">{label}</div>
      <div className="mt-1 text-[11px] leading-4 text-slate-500">{desc}</div>
    </button>
  );
}

function Fact({ label, value, tone = "slate" }: { label: string; value: string; tone?: "slate" | "emerald" | "rose" }) {
  const toneClass =
    tone === "emerald" ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-100" : tone === "rose" ? "border-rose-400/30 bg-rose-500/10 text-rose-100" : "border-white/8 bg-white/[0.02] text-slate-200";
  return (
    <div className={`rounded-xl border px-3 py-2 ${toneClass}`}>
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-0.5 break-all font-mono text-xs">{value}</div>
    </div>
  );
}

function fmtBool(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "yes" : "no";
}
