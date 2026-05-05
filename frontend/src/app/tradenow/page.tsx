"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, CheckCircle2, Play, Power, ShieldCheck, XCircle, Settings, Wallet } from "lucide-react";
import Link from "next/link";
import { MetricCard, PageHeader } from "@/components/Cards";
import { TradeNowWorkspacePanel } from "@/components/workspace/TradeNowWorkspacePanel";
import { StockSearchChart, type StockChartSelection } from "@/components/StockSearchChart";
import { PortfolioHistoryChart } from "@/components/PortfolioHistoryChart";
import { api, type AccountRiskProfile, type AlpacaPaperPosition, type AlpacaPaperSnapshot, type AlpacaPaperPortfolioHistory, type SettingsResponse } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8900";

type TradeTab = "stocks" | "options" | "etf" | "crypto" | "execution" | "portfolio";

const TAB_TO_ASSET: Record<Exclude<TradeTab, "execution" | "portfolio">, "stock" | "option" | "etf" | "crypto"> = {
  stocks: "stock",
  options: "option",
  etf: "etf",
  crypto: "crypto",
};

const ETF_SYMBOLS = new Set([
  "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "EFA", "EEM", "GLD", "SLV", "TLT", "HYG", "XLF", "XLE", "SMH", "ARKK", "SCHD", "VGT", "IVV", "IJH",
]);

function defaultSymbolForTab(tab: Exclude<TradeTab, "execution" | "portfolio">): string {
  switch (tab) {
    case "crypto":
      return "BTC/USD";
    case "options":
      return "AAPL260116C00200000";
    case "etf":
      return "SPY";
    default:
      return "AAPL";
  }
}

/** Route Alpaca position rows into the same buckets as the trade tabs (best-effort without asset_class on position). */
function positionTab(symbol: string): TradeTab {
  const u = symbol.toUpperCase().trim();
  if (u.includes("/") || u.endsWith("USD")) return "crypto";
  if (/^[A-Z]{1,6}\d{6}[CP]\d{8}$/.test(u)) return "options";
  if (/^[A-Z]{1,5}\d+[CP]\d{3,}$/.test(u) && u.length >= 10) return "options";
  if (ETF_SYMBOLS.has(u)) return "etf";
  return "stocks";
}

/** OCC-style option symbol: root + YYMMDD + C|P + strike×1000 (8 digits). Compact form without space padding (matches Alpaca examples). */
function isoDateToYymmdd(iso: string): string {
  if (!iso || iso.length < 10) return "";
  const year = Number(iso.slice(0, 4));
  const mm = iso.slice(5, 7);
  const dd = iso.slice(8, 10);
  if (!Number.isFinite(year) || mm.length !== 2 || dd.length !== 2) return "";
  const yy = String(year % 100).padStart(2, "0");
  return `${yy}${mm}${dd}`;
}

function buildOptionOsiSymbol(root: string, yymmdd: string, right: "C" | "P", strike: number): string {
  const r = root.toUpperCase().replace(/[^A-Z0-9.]/g, "").slice(0, 6);
  const exp = yymmdd.replace(/\D/g, "");
  if (r.length < 1 || exp.length !== 6 || !Number.isFinite(strike) || strike <= 0) return "";
  const strikePart = Math.round(strike * 1000).toString().padStart(8, "0");
  return `${r}${exp}${right}${strikePart}`;
}

function parseOsiSymbol(symbol: string): { root: string; expiryIso: string; right: "C" | "P"; strike: string } | null {
  const u = symbol.toUpperCase().trim();
  const m = u.match(/^([A-Z0-9.]{1,6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$/);
  if (!m) return null;
  const root = m[1];
  const yy = parseInt(m[2], 10);
  const mm = m[3];
  const dd = m[4];
  const right = m[5] as "C" | "P";
  const strikeRaw = parseInt(m[6], 10);
  const year = yy >= 70 ? 1900 + yy : 2000 + yy;
  const strike = (strikeRaw / 1000).toString();
  const expiryIso = `${year}-${mm}-${dd}`;
  return { root, expiryIso, right, strike };
}

type TradeNowConfig = {
  user_enabled: boolean;
  automatic_execution_user_enabled: boolean;
  execution_mode: "disabled" | "dry_run" | "paper" | "live";
  broker: string;
  paper_endpoint: string;
  live_endpoint: string;
  require_human_approval: boolean;
  live_trading_enabled_env: boolean;
  broker_execution_enabled_env: boolean;
  paper_trading_enabled_env: boolean;
  autonomous_execution_enabled_env: boolean;
  alpaca_keys_configured: boolean;
  alpaca_key_id_configured: boolean;
  alpaca_secret_key_configured: boolean;
  status: string;
  autonomous_status: string;
  blockers: string[];
  autonomous_blockers: string[];
  safety_notes: string[];
};

type TradeNowOrderResponse = {
  status: "blocked" | "dry_run" | "submitted" | "failed";
  execution_mode: string;
  order_id?: string | null;
  client_order_id: string;
  symbol: string;
  asset_class: "stock" | "etf" | "crypto" | "option";
  side: string;
  submitted_payload: Record<string, unknown>;
  broker_response?: Record<string, unknown> | null;
  request_id?: string | null;
  blockers: string[];
  warnings: string[];
  safety_notes: string[];
};

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

type PortfolioRange = "1D" | "5D" | "1M" | "3M" | "1Y";

function portfolioHistoryQuery(range: PortfolioRange): { period: string; timeframe: string } {
  switch (range) {
    case "1D":
      return { period: "1D", timeframe: "5Min" };
    case "5D":
      return { period: "5D", timeframe: "15Min" };
    case "1M":
      return { period: "1M", timeframe: "1H" };
    case "1Y":
      // Alpaca uses "1A" for 1 year in many endpoints.
      return { period: "1A", timeframe: "1D" };
    case "3M":
    default:
      return { period: "3M", timeframe: "1D" };
  }
}

function StatusBadge({ value }: { value: string | boolean }) {
  const text = String(value);
  const positive = text === "true" || text.includes("ready") || text === "dry_run";
  const negative = text === "false" || text.includes("blocked") || text.includes("disabled") || text === "failed";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${
        positive ? "border-emerald-500 bg-emerald-500/10 text-emerald-300" : negative ? "border-rose-500 bg-rose-500/10 text-rose-300" : "border-amber-500 bg-amber-500/10 text-amber-300"
      }`}
    >
      {text.replace(/_/g, " ")}
    </span>
  );
}

function EnvLine({ value }: { value: string }) {
  return <div className="rounded-lg border border-emerald-400/15 bg-black/40 px-2 py-1.5 font-mono text-[10px] text-slate-400">{value}</div>;
}

function SettingStatus({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div
      className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
        enabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-rose-500/30 bg-rose-500/10 text-rose-300"
      }`}
    >
      <span className="font-medium">{label}</span>
      <span className={`h-2 w-2 rounded-full ${enabled ? "bg-emerald-500" : "bg-rose-500"}`} />
    </div>
  );
}

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";

function percent(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toFixed(2)}%`;
}

function number(value?: number | null, suffix = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

function calcStockReport(selection: StockChartSelection | null) {
  const snapshot = selection?.snapshot;
  const history = selection?.history;
  const closes = history?.data.map((row) => row.close).filter((value): value is number => value !== null) ?? [];
  const volumes = history?.data.map((row) => row.volume).filter((value): value is number => value !== null) ?? [];
  const lastClose = closes.at(-1) ?? snapshot?.price ?? null;
  const firstClose = closes.at(0) ?? null;
  const momentum = firstClose && lastClose ? ((lastClose - firstClose) / firstClose) * 100 : null;
  const avgVolume = volumes.length ? volumes.reduce((sum, value) => sum + value, 0) / volumes.length : snapshot?.average_volume ?? null;
  const latestVolume = volumes.at(-1) ?? snapshot?.volume ?? null;
  const spread = snapshot?.bid_ask_spread ?? null;
  const sourceQuality = snapshot?.data_quality ?? history?.data_quality ?? "not_loaded";
  const provider = snapshot?.provider ?? history?.provider ?? "—";
  const isMock = Boolean(snapshot?.is_mock || history?.is_mock);
  const hasUsableSourceData = Boolean(snapshot?.price && !isMock && sourceQuality === "real");

  let featureStatus = "waiting_for_source_data";
  if (isMock) featureStatus = "mock_selected_for_testing";
  else if (hasUsableSourceData) featureStatus = "source_data_ready";
  else if (selection) featureStatus = "source_unavailable";

  return {
    momentum,
    latestVolume,
    avgVolume,
    spread,
    featureStatus,
    provider,
    source: selection?.source ?? "auto",
    quality: sourceQuality,
  };
}

export default function TradeNowPage() {
  const [config, setConfig] = useState<TradeNowConfig | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [alpaca, setAlpaca] = useState<AlpacaPaperSnapshot | null>(null);
  const [portfolioHistory, setPortfolioHistory] = useState<AlpacaPaperPortfolioHistory | null>(null);
  const [portfolioRange, setPortfolioRange] = useState<PortfolioRange>("3M");
  const [riskProfile, setRiskProfile] = useState<AccountRiskProfile | null>(null);
  const [order, setOrder] = useState<TradeNowOrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TradeTab>("stocks");

  const [form, setForm] = useState({
    symbol: "AAPL",
    asset_class: "stock" as "stock" | "etf" | "crypto" | "option",
    side: "buy",
    qty: "1",
    limit_price: "",
    stop_price: "",
    type: "market",
    time_in_force: "day",
    dry_run: true,
    human_approval_confirmed: false,
  });

  const [optionBuilder, setOptionBuilder] = useState({
    root: "AAPL",
    expiryIso: "2026-01-16",
    right: "C" as "C" | "P",
    strike: "200",
  });
  const [ticketStockSelection, setTicketStockSelection] = useState<StockChartSelection | null>(null);

  const onTicketChartSelection = useCallback(
    (sel: StockChartSelection) => {
      setTicketStockSelection(sel);
      if (activeTab === "stocks" || activeTab === "etf") {
        setForm((f) => ({ ...f, symbol: sel.symbol.toUpperCase() }));
      }
    },
    [activeTab],
  );

  const loadConfig = async () => {
    const next = await apiFetch<TradeNowConfig>("/api/tradenow/config");
    setConfig(next);
  };

  const loadSettings = async () => {
    const settingsData = await api.getSettings();
    setSettings(settingsData);
  };

  const loadPortfolioHistory = useCallback(async () => {
    try {
      const { period, timeframe } = portfolioHistoryQuery(portfolioRange);
      const history = await api.getAlpacaPaperPortfolioHistory(period, timeframe);
      setPortfolioHistory(history);
    } catch {
      setPortfolioHistory(null);
    }
  }, [portfolioRange]);

  const loadAlpaca = useCallback(async () => {
    try {
      const snap = await api.getAlpacaPaperSnapshot();
      setAlpaca(snap);
    } catch {
      setAlpaca(null);
    }
  }, []);

  const loadRisk = useCallback(async () => {
    try {
      const p = await api.getAccountRisk();
      setRiskProfile(p);
    } catch {
      setRiskProfile(null);
    }
  }, []);

  useEffect(() => {
    loadConfig().catch((err) => setError(err.message));
    loadSettings().catch((err) => setError(err.message));
    loadAlpaca();
    loadRisk();
    loadPortfolioHistory();
  }, [loadAlpaca, loadRisk, loadPortfolioHistory]);

  const setTab = (tab: TradeTab) => {
    setActiveTab(tab);
    if (tab === "execution" || tab === "portfolio") return;

    const ac = TAB_TO_ASSET[tab];
    const nextSymbol = defaultSymbolForTab(tab);
    setForm((f) => ({
      ...f,
      asset_class: ac,
      symbol: nextSymbol,
      time_in_force: ac === "crypto" ? "gtc" : "day",
      type: ac === "option" && !["market", "limit"].includes(f.type) ? "limit" : f.type,
    }));
    if (tab === "options") {
      const parsed = parseOsiSymbol(nextSymbol);
      if (parsed) {
        setOptionBuilder({
          root: parsed.root,
          expiryIso: parsed.expiryIso,
          right: parsed.right,
          strike: parsed.strike,
        });
      }
    }
  };

  const applyOptionBuilder = () => {
    const yymmdd = isoDateToYymmdd(optionBuilder.expiryIso);
    const strike = parseFloat(optionBuilder.strike);
    const sym = buildOptionOsiSymbol(optionBuilder.root, yymmdd, optionBuilder.right, strike);
    if (sym) setForm((f) => ({ ...f, symbol: sym }));
  };

  const updateConfig = async (patch: Partial<TradeNowConfig>) => {
    setSaving(true);
    setError(null);
    try {
      const next = await apiFetch<TradeNowConfig>("/api/tradenow/config", {
        method: "PUT",
        body: JSON.stringify({
          user_enabled: patch.user_enabled ?? config?.user_enabled ?? false,
          automatic_execution_user_enabled: patch.automatic_execution_user_enabled ?? config?.automatic_execution_user_enabled ?? false,
          execution_mode: patch.execution_mode ?? config?.execution_mode ?? "dry_run",
        }),
      });
      setConfig(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update TradeNow config");
    } finally {
      setSaving(false);
    }
  };

  const placeOrder = async () => {
    setSaving(true);
    setError(null);
    setOrder(null);
    try {
      const response = await apiFetch<TradeNowOrderResponse>("/api/tradenow/orders", {
        method: "POST",
        body: JSON.stringify({
          symbol: form.symbol,
          asset_class: form.asset_class,
          side: form.side,
          qty: Number(form.qty),
          type: form.type,
          time_in_force: form.time_in_force,
          limit_price: form.limit_price ? Number(form.limit_price) : null,
          stop_price: form.stop_price ? Number(form.stop_price) : null,
          dry_run: form.dry_run,
          human_approval_confirmed: form.human_approval_confirmed,
          approval_source: "human",
        }),
      });
      setOrder(response);
      await loadConfig();
      await loadAlpaca();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Order request failed");
    } finally {
      setSaving(false);
    }
  };

  const positions = alpaca?.positions ?? [];
  const isTradeTab = activeTab === "stocks" || activeTab === "options" || activeTab === "etf" || activeTab === "crypto";
  const tabPositions = useMemo(() => (isTradeTab ? positions.filter((p) => positionTab(p.symbol) === activeTab) : []), [positions, activeTab, isTradeTab]);

  const tabHint = useMemo(() => {
    switch (activeTab) {
      case "crypto":
        return "Crypto uses slash pairs (e.g. BTC/USD), GTC/IOC, and fractional qty where supported.";
      case "options":
        return "Options use OCC symbols. Alpaca paper supports market/limit; stops may be limited — check blockers after submit.";
      case "etf":
        return "ETFs trade like equities on Alpaca; use standard stock-style day/GTC and share qty.";
      case "execution":
        return "Execution configuration + settings routing gates. No orders are placed from this tab.";
      case "portfolio":
        return "Portfolio snapshot + equity curve from Alpaca paper. Period is tuned for portfolio-level trend, not intraday.";
      default:
        return "Equities: standard symbols, day session defaults, and share qty.";
    }
  }, [activeTab]);

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1500px] space-y-4">
        <PageHeader
          eyebrow="execution foundation"
          title="TradeNow"
          description="Alpaca execution adapter with dry-run default, paper endpoint support, human approval, env-only credentials, and live trading disabled unless explicitly enabled later."
        />

        {error && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

        {/* Asset-class tabs (plus execution/portfolio tabs) */}
        <div className="border-b border-emerald-400/15 pb-2">
          <div className="flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {(
            [
              ["stocks", "Stocks"],
              ["options", "Options"],
              ["etf", "ETF"],
              ["crypto", "Crypto"],
              ["execution", "Execution configuration"],
              ["portfolio", "Portfolio"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                activeTab === id
                  ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                  : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
          </div>
        </div>

        <p className="text-xs leading-relaxed text-slate-400">{tabHint}</p>

        {activeTab === "execution" && (
          <>
            {settings ? (
              <section className={cardShell}>
                <div className="mb-4 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Settings className="h-5 w-5 text-emerald-300" />
                    <h2 className="text-lg font-black text-white">Settings routing to TradeNow</h2>
                  </div>
                  <Link href="/settings" className="text-sm text-emerald-400 underline hover:text-emerald-300">
                    Edit in Settings →
                  </Link>
                </div>
                <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
                  <SettingStatus label="Paper Trading" enabled={settings.trading.paper_trading_enabled} />
                  <SettingStatus label="Live Trading" enabled={settings.trading.live_trading_enabled} />
                  <SettingStatus label="Broker Execution" enabled={settings.trading.broker_execution_enabled} />
                  <SettingStatus label="Human Approval" enabled={settings.trading.require_human_approval} />
                  <SettingStatus label="Execution Agent" enabled={settings.trading.execution_agent_enabled} />
                  <SettingStatus label="Alpaca Paper" enabled={settings.trading.alpaca_paper_trade} />
                </div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="rounded border border-emerald-400/20 bg-black/30 px-2 py-1 text-slate-400">
                    Mode: <span className="text-emerald-400">{settings.trading.execution_mode}</span>
                  </span>
                  <span className="rounded border border-emerald-400/20 bg-black/30 px-2 py-1 text-slate-400">
                    Broker: <span className="text-emerald-400">{settings.trading.broker_provider}</span>
                  </span>
                </div>
              </section>
            ) : null}

            <section className={`${cardShell} p-3`}>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Execution configuration</h3>
              <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
                <div className="rounded-xl border border-emerald-400/10 bg-black/25 p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <Power className="h-4 w-4 text-emerald-300" />
                    <span className="text-xs font-bold text-white">Manual</span>
                  </div>
                  {config ? (
                    <div className="space-y-2 text-[11px] text-slate-300">
                      <div className="flex flex-wrap gap-1">
                        <StatusBadge value={config.status} />
                        <StatusBadge value={config.execution_mode} />
                      </div>
                      <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2 py-1.5">
                        <span>UI enabled</span>
                        <input type="checkbox" checked={config.user_enabled} onChange={(e) => updateConfig({ user_enabled: e.target.checked })} />
                      </label>
                      <select
                        className="w-full rounded-lg border border-emerald-400/20 bg-black/40 px-2 py-1 text-[11px] text-white"
                        value={config.execution_mode}
                        onChange={(e) => updateConfig({ execution_mode: e.target.value as TradeNowConfig["execution_mode"] })}
                        disabled={saving}
                      >
                        <option value="dry_run">Dry run</option>
                        <option value="paper">Paper</option>
                        <option value="live">Live (gated)</option>
                        <option value="disabled">Disabled</option>
                      </select>
                      <div className="space-y-1 border-t border-white/10 pt-2">
                        <div className="flex justify-between">
                          <span className="text-slate-500">Broker env</span>
                          <StatusBadge value={config.broker_execution_enabled_env} />
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Paper env</span>
                          <StatusBadge value={config.paper_trading_enabled_env} />
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-500">Human approval</span>
                          <StatusBadge value={config.require_human_approval} />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-500">Loading…</p>
                  )}
                </div>

                <div className="rounded-xl border border-emerald-400/10 bg-black/25 p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <Bot className="h-4 w-4 text-cyan-300" />
                    <span className="text-xs font-bold text-white">Automatic</span>
                  </div>
                  {config ? (
                    <div className="space-y-2 text-[11px] text-slate-300">
                      <div className="flex flex-wrap gap-1">
                        <StatusBadge value={config.autonomous_status} />
                        <StatusBadge value={`auto_env_${config.autonomous_execution_enabled_env}`} />
                      </div>
                      <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2 py-1.5">
                        <span>Auto paper (future)</span>
                        <input
                          type="checkbox"
                          checked={config.automatic_execution_user_enabled}
                          onChange={(e) => updateConfig({ automatic_execution_user_enabled: e.target.checked })}
                        />
                      </label>
                      <p className="leading-snug text-slate-500">Requires autonomous env + gates. See Safety for blockers.</p>
                      {config.autonomous_blockers?.length ? (
                        <ul className="max-h-24 space-y-1 overflow-y-auto text-amber-200/90">
                          {config.autonomous_blockers.slice(0, 4).map((b) => (
                            <li key={b} className="rounded border border-amber-500/20 bg-amber-500/5 px-2 py-1">
                              {b}
                            </li>
                          ))}
                        </ul>
                      ) : null}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-500">Loading…</p>
                  )}
                </div>

                <div className="rounded-xl border border-amber-500/25 bg-black/25 p-3">
                  <div className="mb-2 flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-amber-300" />
                    <span className="text-xs font-bold text-white">Safety</span>
                  </div>
                  {config?.blockers?.length ? (
                    <ul className="mb-2 max-h-28 space-y-1 overflow-y-auto text-[11px] text-amber-200">
                      {config.blockers.map((blocker) => (
                        <li key={blocker} className="rounded border border-amber-500/25 bg-amber-500/5 px-2 py-1">
                          {blocker}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mb-2 text-[11px] text-emerald-200/90">No blockers for current mode.</p>
                  )}
                  <div className="border-t border-white/10 pt-2">
                    <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Env reference</p>
                    <div className="space-y-1">
                      <EnvLine value="ALPACA_API_KEY / ALPACA_SECRET_KEY" />
                      <EnvLine value="BROKER_EXECUTION_ENABLED / LIVE_TRADING_ENABLED" />
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === "portfolio" && (
          <section className={cardShell}>
            <div className="mb-3 flex items-center gap-2">
              <Wallet className="h-5 w-5 text-emerald-300" />
              <h2 className="text-lg font-black text-white">Current portfolio</h2>
              <Link href="/account-risk" className="ml-auto text-xs text-emerald-400/90 underline hover:text-emerald-300">
                Open Account Risk Center →
              </Link>
            </div>
            {alpaca?.account ? (
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <MetricCard
                  label="Buying power"
                  value={`$${alpaca.account.buying_power?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`}
                  accent
                />
                <MetricCard label="Account equity" value={`$${alpaca.account.equity?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`} />
                <MetricCard label="Max risk / trade" value={riskProfile != null ? `${riskProfile.max_risk_per_trade_percent}%` : "—"} />
                <MetricCard
                  label="Day trades / PDT"
                  value={`${alpaca.account.daytrade_count ?? 0} / ${alpaca.account.pattern_day_trader ? "flagged" : "clear"}`}
                />
              </div>
            ) : (
              <p className="text-sm text-slate-400">
                {alpaca?.message ?? "Connect Alpaca paper keys in backend `.env` to load buying power and risk context."}
              </p>
            )}

            <div className="mt-4 flex flex-wrap items-center gap-2">
              {(["1D", "5D", "1M", "3M", "1Y"] as const).map((range) => (
                <button
                  key={range}
                  type="button"
                  onClick={() => setPortfolioRange(range)}
                  className={`shrink-0 rounded-xl px-3 py-1.5 text-xs font-bold uppercase transition ${
                    portfolioRange === range
                      ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]"
                      : "border border-white/10 bg-white/[0.03] text-slate-400 hover:border-white/15 hover:bg-white/[0.05] hover:text-slate-200"
                  }`}
                >
                  {range}
                </button>
              ))}
              <button
                type="button"
                onClick={() => loadPortfolioHistory()}
                className="ml-auto rounded-xl border border-emerald-400/20 bg-black/30 px-3 py-1.5 text-xs font-bold uppercase text-emerald-300 hover:border-emerald-400/40 hover:bg-black/40"
              >
                Refresh
              </button>
            </div>
            <div className="mt-4">
              <PortfolioHistoryChart history={portfolioHistory} height={360} />
            </div>
          </section>
        )}

        {activeTab === "stocks" && (
          <div className="mt-4">
            <StockSearchChart
              variant="embedded"
              pageEyebrow=""
              pageTitle=""
              pageDescription=""
              onSelectionChange={(sel) => onTicketChartSelection(sel)}
            />
          </div>
        )}

        {isTradeTab && (
        <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="space-y-4">
            <div className={cardShell}>
              <h2 className="mb-3 text-lg font-black text-white">Manual order ticket</h2>
            <div className="mb-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs leading-relaxed text-emerald-100/90">
              Active class: <span className="font-bold uppercase text-emerald-300">{activeTab}</span>. Paper submission needs paper mode, broker env, dry-run off, and human approval when required.
            </div>
            {activeTab === "options" ? (
              <div className="mb-3 space-y-3">
                <div className="rounded-xl border border-cyan-500/25 bg-cyan-500/5 p-3 text-xs leading-relaxed text-slate-200">
                  <p className="mb-2 font-bold uppercase tracking-wide text-cyan-300">Alpaca option contract (quick reference)</p>
                  <ul className="list-inside list-disc space-y-1 text-slate-300">
                    <li>Symbol is OCC format: underlying + YYMMDD + C or P + strike (strike × 1000, 8 digits). Example: AAPL260116C00200000.</li>
                    <li>Qty is number of contracts; standard U.S. equity multiplier is 100 shares per contract.</li>
                    <li>U.S. equity options are American-style (early exercise rules depend on the clearing/venue).</li>
                    <li>Common order types: market and limit; time-in-force often day or GTC. Paper vs live and complex orders depend on account and API support.</li>
                    <li>Check open interest, bid/ask width, and buying power / margin impact before submitting.</li>
                  </ul>
                  <a
                    href="https://docs.alpaca.markets/docs/options-trading"
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 inline-block text-cyan-400 underline hover:text-cyan-300"
                  >
                    Alpaca options trading docs →
                  </a>
                </div>
                <div className="rounded-xl border border-emerald-400/20 bg-black/30 p-3">
                  <p className="mb-2 text-xs font-bold uppercase tracking-wide text-emerald-400">Build OCC symbol</p>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                    <label className="text-sm text-slate-300">
                      Underlying
                      <input
                        value={optionBuilder.root}
                        onChange={(e) => setOptionBuilder((o) => ({ ...o, root: e.target.value }))}
                        className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 font-mono text-white"
                      />
                    </label>
                    <label className="text-sm text-slate-300">
                      Expiration
                      <input
                        type="date"
                        value={optionBuilder.expiryIso}
                        onChange={(e) => setOptionBuilder((o) => ({ ...o, expiryIso: e.target.value }))}
                        className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                      />
                    </label>
                    <label className="text-sm text-slate-300">
                      Right
                      <select
                        value={optionBuilder.right}
                        onChange={(e) => setOptionBuilder((o) => ({ ...o, right: e.target.value as "C" | "P" }))}
                        className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                      >
                        <option value="C">Call</option>
                        <option value="P">Put</option>
                      </select>
                    </label>
                    <label className="text-sm text-slate-300">
                      Strike ($)
                      <input
                        value={optionBuilder.strike}
                        onChange={(e) => setOptionBuilder((o) => ({ ...o, strike: e.target.value }))}
                        type="number"
                        min="0"
                        step="0.01"
                        className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                      />
                    </label>
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={applyOptionBuilder}
                      className="rounded-lg border border-emerald-400/40 bg-emerald-500/15 px-3 py-1.5 text-xs font-bold uppercase text-emerald-300 hover:bg-emerald-500/25"
                    >
                      Apply to ticket symbol
                    </button>
                    <span className="break-all font-mono text-[11px] text-slate-400">
                      Preview:{" "}
                      {buildOptionOsiSymbol(
                        optionBuilder.root,
                        isoDateToYymmdd(optionBuilder.expiryIso),
                        optionBuilder.right,
                        parseFloat(optionBuilder.strike),
                      ) || "—"}
                    </span>
                  </div>
                </div>
              </div>
            ) : null}
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-300">
                {activeTab === "options" ? "OCC symbol" : "Symbol"}
                <input
                  value={form.symbol}
                  onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                />
              </label>
              <label className="text-sm text-slate-300">
                Side
                <select
                  value={form.side}
                  onChange={(e) => setForm({ ...form, side: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                >
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </label>
              <label className="text-sm text-slate-300">
                {form.asset_class === "option" ? "Contracts (qty)" : "Quantity"}
                <input
                  value={form.qty}
                  onChange={(e) => setForm({ ...form, qty: e.target.value })}
                  type="number"
                  min="0"
                  step="0.0001"
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                />
              </label>
              <label className="text-sm text-slate-300">
                Order type
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                >
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                  {form.asset_class !== "option" ? <option value="stop">Stop</option> : null}
                  {form.asset_class !== "option" ? <option value="stop_limit">Stop limit</option> : null}
                </select>
              </label>
              <label className="text-sm text-slate-300">
                Time in force
                <select
                  value={form.time_in_force}
                  onChange={(e) => setForm({ ...form, time_in_force: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                >
                  {form.asset_class === "crypto" ? (
                    <>
                      <option value="gtc">GTC</option>
                      <option value="ioc">IOC</option>
                    </>
                  ) : (
                    <>
                      <option value="day">Day</option>
                      <option value="gtc">GTC</option>
                      <option value="opg">OPG</option>
                      <option value="cls">CLS</option>
                      <option value="ioc">IOC</option>
                      <option value="fok">FOK</option>
                    </>
                  )}
                </select>
              </label>
              <label className="text-sm text-slate-300">
                Limit price
                <input
                  value={form.limit_price}
                  onChange={(e) => setForm({ ...form, limit_price: e.target.value })}
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="For limit"
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                />
              </label>
              <label className="text-sm text-slate-300">
                Stop price
                <input
                  value={form.stop_price}
                  onChange={(e) => setForm({ ...form, stop_price: e.target.value })}
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="For stop"
                  disabled={form.asset_class === "option"}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white disabled:opacity-50"
                />
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-300">
                <input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} />
                Dry run
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                <input
                  type="checkbox"
                  checked={form.human_approval_confirmed}
                  onChange={(e) => setForm({ ...form, human_approval_confirmed: e.target.checked })}
                />
                Human approval
              </label>
            </div>
            <button
              onClick={placeOrder}
              disabled={saving}
              className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-bold uppercase text-emerald-300 hover:bg-emerald-500 hover:text-slate-950 disabled:opacity-50"
            >
              <Play className="h-4 w-4" /> Submit order
            </button>
              {order ? (
                <div className="mt-4 space-y-2 rounded-xl border border-emerald-400/20 bg-black/35 p-3">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={order.status} />
                  <StatusBadge value={order.execution_mode} />
                  <StatusBadge value={order.asset_class} />
                  {order.order_id ? (
                    <span className="rounded-full border border-white/15 bg-black/30 px-2 py-0.5 font-mono text-[10px] text-slate-300">ID: {order.order_id}</span>
                  ) : null}
                </div>
                {order.status === "submitted" ? (
                  <p className="flex items-center gap-2 text-sm text-emerald-300">
                    <CheckCircle2 className="h-4 w-4" /> Submitted to broker.
                  </p>
                ) : null}
                {order.status === "blocked" || order.status === "failed" ? (
                  <p className="flex items-center gap-2 text-sm text-rose-300">
                    <XCircle className="h-4 w-4" /> Not submitted.
                  </p>
                ) : null}
                {order.status === "dry_run" ? (
                  <p className="flex items-center gap-2 text-sm text-cyan-300">
                    <AlertTriangle className="h-4 w-4" /> Dry run only.
                  </p>
                ) : null}
                {order.request_id ? (
                  <p className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-2 py-1.5 font-mono text-[10px] text-cyan-200">X-Request-ID: {order.request_id}</p>
                ) : null}
                {order.blockers?.length ? (
                  <ul className="max-h-32 space-y-1 overflow-y-auto text-xs text-amber-200">
                    {order.blockers.map((b) => (
                      <li key={b} className="rounded border border-amber-500/25 bg-amber-500/5 px-2 py-1">
                        {b}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {order.warnings?.length ? (
                  <ul className="text-xs text-slate-400">
                    {order.warnings.map((w) => (
                      <li key={w}>⚠ {w}</li>
                    ))}
                  </ul>
                ) : null}
                </div>
              ) : null}

            </div>

            {(activeTab === "stocks" || activeTab === "etf") && (
              <div className={cardShell}>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className="text-lg font-black text-white">Feature pipeline</h3>
                  {ticketStockSelection?.symbol ? (
                    <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 text-xs font-bold uppercase text-slate-300">
                      {ticketStockSelection.symbol} · {calcStockReport(ticketStockSelection).source} · {calcStockReport(ticketStockSelection).provider}
                    </span>
                  ) : (
                    <span className="text-xs text-slate-500">Load a symbol in the chart below.</span>
                  )}
                </div>
                {(() => {
                  const rep = calcStockReport(ticketStockSelection);
                  return (
                    <div className="grid grid-cols-2 gap-3">
                      <div className="rounded-xl border border-emerald-400/15 bg-black/40 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">Momentum</p>
                        <p className="mt-2 text-2xl font-black text-white">{percent(rep.momentum)}</p>
                      </div>
                      <div className="rounded-xl border border-emerald-400/15 bg-black/40 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">Feature status</p>
                        <p className="mt-2 text-sm font-black capitalize text-white">{rep.featureStatus.replace(/_/g, " ")}</p>
                      </div>
                      <div className="rounded-xl border border-emerald-400/15 bg-black/40 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">Latest volume</p>
                        <p className="mt-2 text-xl font-black text-white">{number(rep.latestVolume)}</p>
                      </div>
                      <div className="rounded-xl border border-emerald-400/15 bg-black/40 p-4">
                        <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">Avg volume</p>
                        <p className="mt-2 text-xl font-black text-white">{number(rep.avgVolume)}</p>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>

          <div className={cardShell}>
            <TradeNowWorkspacePanel tab={activeTab} />
          </div>
        </section>
        )}

        {isTradeTab && (
        <section className={cardShell}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-black text-white">Current holdings</h2>
            <span className="text-xs text-slate-500">
              {tabPositions.length} in {activeTab} (best-effort filter)
            </span>
          </div>
          {tabPositions.length === 0 ? (
            <p className="text-sm text-slate-400">No open positions classified as {activeTab} in this paper account.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-emerald-400/15">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-emerald-400">
                  <tr>
                    <th className="px-3 py-2">Symbol</th>
                    <th className="px-3 py-2">Qty</th>
                    <th className="px-3 py-2">Market value</th>
                    <th className="px-3 py-2">Unrealized P/L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-950/40">
                  {tabPositions.map((p: AlpacaPaperPosition) => (
                    <tr key={p.symbol} className="hover:bg-white/[0.03]">
                      <td className="px-3 py-2 font-mono text-white">{p.symbol}</td>
                      <td className="px-3 py-2 text-slate-300">{p.qty ?? "—"}</td>
                      <td className="px-3 py-2 text-slate-300">
                        {p.market_value != null ? `$${p.market_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-300">
                        {p.unrealized_pl != null ? `$${p.unrealized_pl.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
        )}
      </div>
    </div>
  );
}
