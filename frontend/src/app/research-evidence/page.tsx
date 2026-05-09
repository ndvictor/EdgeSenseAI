"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  getQlibStatus,
  getQlibAutomationStatus,
  listQlibArtifacts,
  getLatestQlibSignals,
  scoreQlibSignals,
  recordQlibBacktest,
  registerQlibModelArtifact,
  runQlibAutomationBacktest,
  runQlibAutomationScore,
  getProofRegistryStatus,
  listProofRegistryRecords,
  createProofRegistryRecord,
  getModelEvidenceStatus,
  listModelEvidenceRecords,
  createModelEvidenceRecord,
  getStrategyEvidenceStatus,
  listStrategyEvidenceRecords,
  createStrategyEvidenceRecord,
} from "@/lib/api";

type Tab = "qlib" | "proof" | "model" | "strategy";

function tabFromSearchParams(sp: URLSearchParams | null): Tab | null {
  const t = sp?.get("tab");
  if (t === "qlib" || t === "proof" || t === "model" || t === "strategy") return t;
  return null;
}

export default function ResearchEvidencePage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [tab, setTab] = useState<Tab>("qlib");

  const selectTab = useCallback(
    (next: Tab) => {
      setTab(next);
      router.replace(`${pathname}?tab=${next}`, { scroll: false });
    },
    [pathname, router],
  );

  useEffect(() => {
    const fromUrl = tabFromSearchParams(searchParams);
    if (fromUrl) setTab(fromUrl);
  }, [searchParams]);
  const [err, setErr] = useState<string | null>(null);

  const [qlibStatus, setQlibStatus] = useState<Record<string, unknown> | null>(null);
  const [qlibAuto, setQlibAuto] = useState<Record<string, unknown> | null>(null);
  const [artifacts, setArtifacts] = useState<Record<string, unknown>[]>([]);
  const [latestSig, setLatestSig] = useState<Record<string, unknown> | null>(null);

  const [scoreJson, setScoreJson] = useState('{"symbol":"AMD","horizon":"day_trading","scores":{}}');
  const [btJson, setBtJson] = useState('{"symbol":"AMD","backtest_run_id":"bt_ui_1","strategy_key":"stock_day_trading"}');
  const [modelArtJson, setModelArtJson] = useState('{"model_name":"ui_model","artifact_path":"/tmp/qlib_stub","artifact_type":"checkpoint"}');

  const [proofSt, setProofSt] = useState<Record<string, unknown> | null>(null);
  const [proofRecs, setProofRecs] = useState<Record<string, unknown>[]>([]);
  const [proofForm, setProofForm] = useState('{"symbol":"AMD","strategy_key":"stock_day_trading","proof_status":"proof_required","source":"ui"}');

  const [modelSt, setModelSt] = useState<Record<string, unknown> | null>(null);
  const [modelRecs, setModelRecs] = useState<Record<string, unknown>[]>([]);
  const [modelForm, setModelForm] = useState(
    '{"model_key":"ui_ranker","model_name":"ui_ranker","model_family":"deterministic_baseline","asset_class":"stock","horizon":"day_trading","status":"recorded","score":0.5}',
  );

  const [stratSt, setStratSt] = useState<Record<string, unknown> | null>(null);
  const [stratRecs, setStratRecs] = useState<Record<string, unknown>[]>([]);
  const [stratForm, setStratForm] = useState(
    '{"strategy_key":"stock_day_trading","strategy_group":"stock","asset_class":"stock","horizon":"day_trading","status":"recorded","strategy_score":0.5}',
  );

  const [busy, setBusy] = useState<string | null>(null);

  async function loadQlib() {
    setErr(null);
    try {
      const [st, au, art, sig] = await Promise.all([
        getQlibStatus(),
        getQlibAutomationStatus(),
        listQlibArtifacts(50),
        getLatestQlibSignals(),
      ]);
      setQlibStatus(st);
      setQlibAuto(au);
      setArtifacts(art.artifacts ?? []);
      setLatestSig(sig.artifact ?? null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Qlib load failed");
    }
  }

  async function loadProof() {
    setErr(null);
    try {
      const [st, rec] = await Promise.all([getProofRegistryStatus(), listProofRegistryRecords(50)]);
      setProofSt(st);
      setProofRecs(rec.records ?? []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Proof load failed");
    }
  }

  async function loadModel() {
    setErr(null);
    try {
      const [st, rec] = await Promise.all([getModelEvidenceStatus(), listModelEvidenceRecords(50)]);
      setModelSt(st);
      setModelRecs(rec.records ?? []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Model evidence load failed");
    }
  }

  async function loadStrategy() {
    setErr(null);
    try {
      const [st, rec] = await Promise.all([getStrategyEvidenceStatus(), listStrategyEvidenceRecords(50)]);
      setStratSt(st);
      setStratRecs(rec.records ?? []);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Strategy evidence load failed");
    }
  }

  useEffect(() => {
    void loadQlib();
  }, []);

  useEffect(() => {
    if (tab === "qlib") void loadQlib();
    if (tab === "proof") void loadProof();
    if (tab === "model") void loadModel();
    if (tab === "strategy") void loadStrategy();
  }, [tab]);

  async function doScore() {
    setBusy("score");
    setErr(null);
    try {
      const body = JSON.parse(scoreJson) as Record<string, unknown>;
      await scoreQlibSignals(body);
      await loadQlib();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "score failed");
    } finally {
      setBusy(null);
    }
  }

  async function doBt() {
    setBusy("bt");
    setErr(null);
    try {
      const body = JSON.parse(btJson) as Record<string, unknown>;
      await recordQlibBacktest(body);
      await loadQlib();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "backtest record failed");
    } finally {
      setBusy(null);
    }
  }

  async function doRegModel() {
    setBusy("reg");
    setErr(null);
    try {
      const body = JSON.parse(modelArtJson) as Record<string, unknown>;
      await registerQlibModelArtifact(body);
      await loadQlib();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "register failed");
    } finally {
      setBusy(null);
    }
  }

  async function doAuto(which: "bt" | "sc") {
    setBusy(`auto_${which}`);
    setErr(null);
    try {
      const payload = { source: "ui", note: "research-evidence" };
      if (which === "bt") await runQlibAutomationBacktest(payload);
      else await runQlibAutomationScore(payload);
      await loadQlib();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "automation failed");
    } finally {
      setBusy(null);
    }
  }

  async function postProof() {
    setBusy("proof");
    setErr(null);
    try {
      await createProofRegistryRecord(JSON.parse(proofForm) as Record<string, unknown>);
      await loadProof();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "proof create failed");
    } finally {
      setBusy(null);
    }
  }

  async function postModel() {
    setBusy("modev");
    setErr(null);
    try {
      await createModelEvidenceRecord(JSON.parse(modelForm) as Record<string, unknown>);
      await loadModel();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "model evidence create failed");
    } finally {
      setBusy(null);
    }
  }

  async function postStrat() {
    setBusy("strat");
    setErr(null);
    try {
      await createStrategyEvidenceRecord(JSON.parse(stratForm) as Record<string, unknown>);
      await loadStrategy();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "strategy evidence create failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Research Evidence</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Qlib artifacts, proof registry, and model/strategy evidence — research and metadata only. No broker execution or live promotion.
          </p>
        </div>
        <Link href="/workflow-runbook" className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-200">
          Runbook →
        </Link>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        {(
          [
            ["qlib", "Qlib"],
            ["proof", "Proof Registry"],
            ["model", "Model Evidence"],
            ["strategy", "Strategy Evidence"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => selectTab(id)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
              tab === id
                ? "border-emerald-400/50 bg-emerald-400/15 text-emerald-100"
                : "border-white/10 bg-[#0a1018] text-slate-400 hover:border-emerald-400/25"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {err ? (
        <div className="mb-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{err}</div>
      ) : null}

      {tab === "qlib" ? (
        <div className="space-y-6">
          <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-[#070c12] p-4 text-xs">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Qlib status</div>
              <pre className="mt-2 max-h-48 overflow-auto text-[11px] text-slate-300">{JSON.stringify(qlibStatus, null, 2)}</pre>
            </div>
            <div className="rounded-xl border border-white/10 bg-[#070c12] p-4 text-xs">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Automation status</div>
              <pre className="mt-2 max-h-48 overflow-auto text-[11px] text-slate-300">{JSON.stringify(qlibAuto, null, 2)}</pre>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy === "auto_bt"}
              onClick={() => doAuto("bt")}
              className="rounded-lg border border-sky-400/40 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-100"
            >
              Automation backtest (safe metadata)
            </button>
            <button
              type="button"
              disabled={busy === "auto_sc"}
              onClick={() => doAuto("sc")}
              className="rounded-lg border border-sky-400/40 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-100"
            >
              Automation score (safe metadata)
            </button>
            <button type="button" onClick={loadQlib} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300">
              Refresh Qlib
            </button>
          </div>
          <div className="rounded-xl border border-emerald-400/15 bg-[#070c12] p-4">
            <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest signals artifact</div>
            <pre className="mt-2 max-h-40 overflow-auto text-[11px] text-slate-300">{JSON.stringify(latestSig, null, 2)}</pre>
          </div>
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
            <h3 className="text-xs font-semibold uppercase text-slate-500">Artifacts</h3>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full min-w-[640px] border-collapse text-left text-[11px]">
                <thead>
                  <tr className="border-b border-white/10 text-slate-500">
                    <th className="pb-2">artifact_id</th>
                    <th className="pb-2">type</th>
                    <th className="pb-2">path</th>
                  </tr>
                </thead>
                <tbody>
                  {artifacts.map((a) => (
                    <tr key={String(a.artifact_id ?? Math.random())} className="border-b border-white/[0.04] text-slate-300">
                      <td className="py-2 font-mono text-emerald-200/80">{String(a.artifact_id ?? "—")}</td>
                      <td className="py-2">{String(a.artifact_type ?? "—")}</td>
                      <td className="py-2 font-mono text-[10px]">{String(a.artifact_path ?? "—")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-white/10 bg-[#0a1018] p-3">
              <div className="text-xs text-slate-500">Score signals (JSON)</div>
              <textarea className="mt-2 w-full rounded border border-white/10 bg-black/30 p-2 font-mono text-[10px] text-slate-100" rows={6} value={scoreJson} onChange={(e) => setScoreJson(e.target.value)} />
              <button type="button" disabled={busy === "score"} onClick={doScore} className="mt-2 rounded border border-emerald-400/40 px-2 py-1 text-[11px] text-emerald-100">
                POST score
              </button>
            </div>
            <div className="rounded-xl border border-white/10 bg-[#0a1018] p-3">
              <div className="text-xs text-slate-500">Record backtest (JSON)</div>
              <textarea className="mt-2 w-full rounded border border-white/10 bg-black/30 p-2 font-mono text-[10px] text-slate-100" rows={6} value={btJson} onChange={(e) => setBtJson(e.target.value)} />
              <button type="button" disabled={busy === "bt"} onClick={doBt} className="mt-2 rounded border border-emerald-400/40 px-2 py-1 text-[11px] text-emerald-100">
                POST backtests/record
              </button>
            </div>
            <div className="rounded-xl border border-white/10 bg-[#0a1018] p-3">
              <div className="text-xs text-slate-500">Register model artifact (JSON)</div>
              <textarea className="mt-2 w-full rounded border border-white/10 bg-black/30 p-2 font-mono text-[10px] text-slate-100" rows={6} value={modelArtJson} onChange={(e) => setModelArtJson(e.target.value)} />
              <button type="button" disabled={busy === "reg"} onClick={doRegModel} className="mt-2 rounded border border-emerald-400/40 px-2 py-1 text-[11px] text-emerald-100">
                POST register-artifact
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {tab === "proof" ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-[#070c12] p-4 text-xs">
            <pre className="max-h-32 overflow-auto text-[11px]">{JSON.stringify(proofSt, null, 2)}</pre>
          </div>
          <div className="rounded-xl border border-white/10 bg-[#0a1018] p-3">
            <div className="text-xs text-slate-500">Create proof record (JSON)</div>
            <textarea className="mt-2 w-full rounded border border-white/10 bg-black/30 p-2 font-mono text-[10px]" rows={5} value={proofForm} onChange={(e) => setProofForm(e.target.value)} />
            <button type="button" disabled={busy === "proof"} onClick={postProof} className="mt-2 rounded border border-emerald-400/40 px-3 py-1 text-xs text-emerald-100">
              POST proof-registry/records
            </button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-emerald-400/10">
            <table className="w-full min-w-[700px] border-collapse text-left text-[11px]">
              <thead>
                <tr className="border-b border-white/10 text-slate-500">
                  <th className="px-2 py-2">proof_id</th>
                  <th className="px-2 py-2">symbol</th>
                  <th className="px-2 py-2">strategy</th>
                  <th className="px-2 py-2">status</th>
                </tr>
              </thead>
              <tbody>
                {proofRecs.map((r) => (
                  <tr key={String(r.proof_id)} className="border-b border-white/[0.04] text-slate-300">
                    <td className="px-2 py-2 font-mono text-emerald-200/80">{String(r.proof_id)}</td>
                    <td className="px-2 py-2">{String(r.symbol)}</td>
                    <td className="px-2 py-2">{String(r.strategy_key)}</td>
                    <td className="px-2 py-2">{String(r.proof_status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {tab === "model" ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-[#070c12] p-4 text-xs">
            <pre className="max-h-32 overflow-auto text-[11px]">{JSON.stringify(modelSt, null, 2)}</pre>
          </div>
          <div className="rounded-xl border border-white/10 bg-[#0a1018] p-3">
            <div className="text-xs text-slate-500">Create model evidence (JSON)</div>
            <textarea className="mt-2 w-full rounded border border-white/10 bg-black/30 p-2 font-mono text-[10px]" rows={5} value={modelForm} onChange={(e) => setModelForm(e.target.value)} />
            <button type="button" disabled={busy === "modev"} onClick={postModel} className="mt-2 rounded border border-emerald-400/40 px-3 py-1 text-xs text-emerald-100">
              POST model-evidence/records
            </button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-emerald-400/10">
            <table className="w-full min-w-[700px] border-collapse text-left text-[11px]">
              <thead>
                <tr className="border-b border-white/10 text-slate-500">
                  <th className="px-2 py-2">evidence_id</th>
                  <th className="px-2 py-2">model</th>
                  <th className="px-2 py-2">score</th>
                </tr>
              </thead>
              <tbody>
                {modelRecs.map((r) => (
                  <tr key={String(r.evidence_id)} className="border-b border-white/[0.04] text-slate-300">
                    <td className="px-2 py-2 font-mono text-emerald-200/80">{String(r.evidence_id)}</td>
                    <td className="px-2 py-2">{String(r.model_name)}</td>
                    <td className="px-2 py-2">{String(r.score)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {tab === "strategy" ? (
        <div className="space-y-4">
          <div className="rounded-xl border border-white/10 bg-[#070c12] p-4 text-xs">
            <pre className="max-h-32 overflow-auto text-[11px]">{JSON.stringify(stratSt, null, 2)}</pre>
          </div>
          <div className="rounded-xl border border-white/10 bg-[#0a1018] p-3">
            <div className="text-xs text-slate-500">Create strategy evidence (JSON)</div>
            <textarea className="mt-2 w-full rounded border border-white/10 bg-black/30 p-2 font-mono text-[10px]" rows={5} value={stratForm} onChange={(e) => setStratForm(e.target.value)} />
            <button type="button" disabled={busy === "strat"} onClick={postStrat} className="mt-2 rounded border border-emerald-400/40 px-3 py-1 text-xs text-emerald-100">
              POST strategy-evidence/records
            </button>
          </div>
          <div className="overflow-x-auto rounded-xl border border-emerald-400/10">
            <table className="w-full min-w-[700px] border-collapse text-left text-[11px]">
              <thead>
                <tr className="border-b border-white/10 text-slate-500">
                  <th className="px-2 py-2">evidence_id</th>
                  <th className="px-2 py-2">strategy_key</th>
                  <th className="px-2 py-2">strategy_score</th>
                </tr>
              </thead>
              <tbody>
                {stratRecs.map((r) => (
                  <tr key={String(r.evidence_id)} className="border-b border-white/[0.04] text-slate-300">
                    <td className="px-2 py-2 font-mono text-emerald-200/80">{String(r.evidence_id)}</td>
                    <td className="px-2 py-2">{String(r.strategy_key)}</td>
                    <td className="px-2 py-2">{String(r.strategy_score ?? "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}
    </div>
  );
}
