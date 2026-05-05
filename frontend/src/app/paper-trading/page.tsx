"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Settings } from "lucide-react";
import { api, type AlpacaPaperSnapshot, type CommandCenterResponse, type PaperOrderRequest, type PaperOrderResponse, type SettingsResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

function money(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function maybeMoney(value?: number | null) {
  return value == null ? "Pending" : money(value);
}

function maybeNumber(value?: number | null) {
  return value == null ? "Pending" : value.toLocaleString(undefined, { maximumFractionDigits: 4 });
}

function StatusBadge({ value }: { value: string | boolean | null | undefined }) {
  const text = String(value ?? "unknown");
  const positive = ["connected", "true", "active", "open", "accepted", "new", "filled", "submitted", "dry_run"].includes(text.toLowerCase());
  const warning = ["not_configured", "unavailable", "false", "blocked", "rejected", "canceled", "failed"].includes(text.toLowerCase());
  return (
    <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${
      positive
        ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-300"
        : warning
          ? "border-amber-400/30 bg-amber-400/10 text-amber-200"
          : "border-slate-600 bg-slate-900 text-slate-300"
    }`}>
      {text.replaceAll("_", " ")}
    </span>
  );
}

function SettingStatus({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
      enabled 
        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" 
        : "border-rose-500/30 bg-rose-500/10 text-rose-300"
    }`}>
      <span className="font-medium">{label}</span>
      <span className={`h-2 w-2 rounded-full ${enabled ? "bg-emerald-500" : "bg-rose-500"}`} />
    </div>
  );
}

export default function PaperTradingPage() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [alpaca, setAlpaca] = useState<AlpacaPaperSnapshot | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [alpacaError, setAlpacaError] = useState<string | null>(null);
  
  // Order form state
  const [orderForm, setOrderForm] = useState<PaperOrderRequest>({
    symbol: "",
    side: "buy",
    qty: 1,
    type: "market",
    time_in_force: "day",
    limit_price: null,
    stop_price: null,
    asset_class: "stock",
    human_approval_confirmed: false,
    dry_run: true,
  });
  const [orderResult, setOrderResult] = useState<PaperOrderResponse | null>(null);
  const [orderLoading, setOrderLoading] = useState(false);
  const [orderError, setOrderError] = useState<string | null>(null);

  useEffect(() => {
    api.getCommandCenter().then(setData).catch((err) => setError(err.message));
    api.getAlpacaPaperSnapshot().then(setAlpaca).catch((err) => setAlpacaError(err.message));
    api.getSettings().then(setSettings).catch((err) => setError(err.message));
  }, []);

  const handleSubmitOrder = async () => {
    if (!orderForm.symbol || orderForm.qty <= 0) {
      setOrderError("Please enter a valid symbol and quantity");
      return;
    }
    
    setOrderLoading(true);
    setOrderError(null);
    setOrderResult(null);
    
    try {
      const result = await api.placePaperOrder(orderForm);
      setOrderResult(result);
    } catch (err) {
      setOrderError(err instanceof Error ? err.message : "Failed to place order");
    } finally {
      setOrderLoading(false);
    }
  };

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="paper validation"
          title="Paper Trading"
          description="Paper trading validates recommendations against your Alpaca paper account before live execution is ever considered. Every broker action remains behind backend safety gates."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {/* Settings Status Panel */}
        {settings && (
          <section className="mb-4 rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings className="h-5 w-5 text-emerald-400" />
                <h2 className="text-xl font-semibold text-emerald-400">Settings Routing to Paper Trading</h2>
              </div>
              <Link href="/settings" className="text-sm text-emerald-400 hover:text-emerald-300 underline">
                Edit in Settings →
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
              <SettingStatus label="Paper Trading" enabled={settings.trading.paper_trading_enabled} />
              <SettingStatus label="Broker Execution" enabled={settings.trading.broker_execution_enabled} />
              <SettingStatus label="Human Approval" enabled={settings.trading.require_human_approval} />
              <SettingStatus label="Alpaca Paper" enabled={settings.trading.alpaca_paper_trade} />
              <SettingStatus label="Execution Agent" enabled={settings.trading.execution_agent_enabled} />
              <SettingStatus label="Market Data" enabled={settings.market_data.alpaca_market_data_enabled} />
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-400">
                Mode: <span className="text-emerald-400">{settings.trading.execution_mode}</span>
              </span>
              <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-400">
                Broker: <span className="text-emerald-400">{settings.trading.broker_provider}</span>
              </span>
              <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-400">
                Starting Cash: <span className="text-emerald-400">${settings.trading.paper_starting_cash.toLocaleString()}</span>
              </span>
            </div>
          </section>
        )}
        
        {/* Order Placement Form */}
        <section className="mb-4 rounded-xl border border-slate-700 bg-slate-900 p-4 shadow-sm">
          <h2 className="mb-4 text-xl font-semibold text-emerald-400">Place Paper Order</h2>
          
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Symbol</label>
              <input
                type="text"
                value={orderForm.symbol}
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value.toUpperCase() })}
                placeholder="AAPL"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Side</label>
              <select
                value={orderForm.side}
                onChange={(e) => setOrderForm({ ...orderForm, side: e.target.value as "buy" | "sell" })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="buy">Buy</option>
                <option value="sell">Sell</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Quantity</label>
              <input
                type="number"
                value={orderForm.qty}
                onChange={(e) => setOrderForm({ ...orderForm, qty: parseFloat(e.target.value) || 0 })}
                min="0.01"
                step="0.01"
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Order Type</label>
              <select
                value={orderForm.type}
                onChange={(e) => setOrderForm({ ...orderForm, type: e.target.value as PaperOrderRequest["type"] })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="market">Market</option>
                <option value="limit">Limit</option>
                <option value="stop">Stop</option>
                <option value="stop_limit">Stop Limit</option>
              </select>
            </div>
          </div>
          
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Time in Force</label>
              <select
                value={orderForm.time_in_force}
                onChange={(e) => setOrderForm({ ...orderForm, time_in_force: e.target.value as PaperOrderRequest["time_in_force"] })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="day">Day</option>
                <option value="gtc">Good Till Canceled</option>
                <option value="ioc">Immediate or Cancel</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Asset Class</label>
              <select
                value={orderForm.asset_class}
                onChange={(e) => setOrderForm({ ...orderForm, asset_class: e.target.value as PaperOrderRequest["asset_class"] })}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
              >
                <option value="stock">Stock</option>
                <option value="etf">ETF</option>
                <option value="crypto">Crypto</option>
                <option value="option">Option</option>
              </select>
            </div>
            {(orderForm.type === "limit" || orderForm.type === "stop_limit") && (
              <div>
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Limit Price</label>
                <input
                  type="number"
                  value={orderForm.limit_price || ""}
                  onChange={(e) => setOrderForm({ ...orderForm, limit_price: parseFloat(e.target.value) || null })}
                  step="0.01"
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>
            )}
            {(orderForm.type === "stop" || orderForm.type === "stop_limit") && (
              <div>
                <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">Stop Price</label>
                <input
                  type="number"
                  value={orderForm.stop_price || ""}
                  onChange={(e) => setOrderForm({ ...orderForm, stop_price: parseFloat(e.target.value) || null })}
                  step="0.01"
                  placeholder="0.00"
                  className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
                />
              </div>
            )}
          </div>
          
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={orderForm.human_approval_confirmed}
                onChange={(e) => setOrderForm({ ...orderForm, human_approval_confirmed: e.target.checked })}
                className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-emerald-600 focus:ring-emerald-500"
              />
              I confirm this order is reviewed and approved by me
            </label>
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={!orderForm.dry_run}
                onChange={(e) => setOrderForm({ ...orderForm, dry_run: !e.target.checked })}
                className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-amber-600 focus:ring-amber-500"
              />
              <span className={!orderForm.dry_run ? "text-amber-400 font-semibold" : ""}>
                Submit to Alpaca (disable dry-run)
              </span>
            </label>
          </div>
          
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleSubmitOrder}
              disabled={orderLoading || !orderForm.symbol}
              className="rounded-lg border border-emerald-600 bg-emerald-900/30 px-6 py-2 text-sm font-semibold text-emerald-400 hover:bg-emerald-900/50 disabled:opacity-50"
            >
              {orderLoading ? "Submitting..." : orderForm.dry_run ? "Preview Order (Dry Run)" : "Submit Order to Alpaca"}
            </button>
            <button
              onClick={() => {
                setOrderForm({
                  symbol: "",
                  side: "buy",
                  qty: 1,
                  type: "market",
                  time_in_force: "day",
                  limit_price: null,
                  stop_price: null,
                  asset_class: "stock",
                  human_approval_confirmed: false,
                  dry_run: true,
                });
                setOrderResult(null);
                setOrderError(null);
              }}
              className="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700"
            >
              Reset Form
            </button>
          </div>
          
          {/* Order Result Display */}
          {orderError && (
            <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
              {orderError}
            </div>
          )}
          
          {orderResult && (
            <div className={`mt-4 rounded-xl border p-4 ${
              orderResult.status === "submitted" ? "border-emerald-500/30 bg-emerald-500/10" :
              orderResult.status === "dry_run" ? "border-cyan-500/30 bg-cyan-500/10" :
              "border-amber-500/30 bg-amber-500/10"
            }`}>
              <div className="flex items-center justify-between">
                <h3 className={`font-semibold ${
                  orderResult.status === "submitted" ? "text-emerald-400" :
                  orderResult.status === "dry_run" ? "text-cyan-400" :
                  "text-amber-400"
                }`}>
                  Order Status: {orderResult.status.toUpperCase()}
                </h3>
                <StatusBadge value={orderResult.status} />
              </div>
              
              <div className="mt-3 grid grid-cols-2 gap-2 text-sm md:grid-cols-4">
                <div className="rounded bg-slate-950/50 px-3 py-2">
                  <span className="text-slate-500">Symbol:</span> <span className="text-white font-semibold">{orderResult.symbol}</span>
                </div>
                <div className="rounded bg-slate-950/50 px-3 py-2">
                  <span className="text-slate-500">Side:</span> <span className="text-white capitalize">{orderResult.side}</span>
                </div>
                <div className="rounded bg-slate-950/50 px-3 py-2">
                  <span className="text-slate-500">Mode:</span> <span className="text-white">{orderResult.execution_mode}</span>
                </div>
                <div className="rounded bg-slate-950/50 px-3 py-2">
                  <span className="text-slate-500">Order ID:</span> <span className="text-white font-mono text-xs">{orderResult.order_id || "N/A"}</span>
                </div>
              </div>
              
              {orderResult.blockers.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs uppercase tracking-wide text-red-500">Blockers</p>
                  <ul className="mt-1 space-y-1 text-sm text-red-300">
                    {orderResult.blockers.map((blocker, i) => (
                      <li key={i}>• {blocker}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {orderResult.warnings.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs uppercase tracking-wide text-amber-500">Warnings</p>
                  <ul className="mt-1 space-y-1 text-sm text-amber-300">
                    {orderResult.warnings.map((warning, i) => (
                      <li key={i}>• {warning}</li>
                    ))}
                  </ul>
                </div>
              )}
              
              {orderResult.broker_response && (
                <div className="mt-3">
                  <p className="text-xs uppercase tracking-wide text-slate-500">Broker Response</p>
                  <pre className="mt-1 max-h-32 overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-300">
                    {JSON.stringify(orderResult.broker_response, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </section>
        
        <section className="mb-4 rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-emerald-500">Alpaca Paper Account</p>
              <h2 className="mt-1 text-2xl font-black text-white">{alpaca?.account?.account_number ? `Account ${alpaca.account.account_number}` : "Paper Broker Connection"}</h2>
              <p className="mt-2 max-w-4xl text-sm leading-relaxed text-slate-300">
                {alpacaError || alpaca?.message || "Checking Alpaca paper connection..."}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <StatusBadge value={alpaca?.status || "loading"} />
              <StatusBadge value={alpaca?.mode || "paper"} />
              <StatusBadge value={alpaca?.live_trading_enabled ? "live enabled" : "live disabled"} />
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-6">
            <MetricCard label="Equity" value={maybeMoney(alpaca?.account?.equity)} accent />
            <MetricCard label="Buying power" value={maybeMoney(alpaca?.account?.buying_power)} />
            <MetricCard label="Cash" value={maybeMoney(alpaca?.account?.cash)} />
            <MetricCard label="Portfolio" value={maybeMoney(alpaca?.account?.portfolio_value)} />
            <MetricCard label="Positions" value={String(alpaca?.positions.length ?? 0)} />
            <MetricCard label="Open orders" value={String(alpaca?.open_orders.length ?? 0)} />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-400">Paper trading env</span>
                <StatusBadge value={alpaca?.paper_trading_enabled} />
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-400">Broker submission env</span>
                <StatusBadge value={alpaca?.broker_execution_enabled} />
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="text-slate-400">Keys configured</span>
                <StatusBadge value={alpaca?.keys_configured} />
              </div>
            </div>
          </div>

          {alpaca?.positions.length ? (
            <div className="mt-5 overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Qty</th>
                    <th className="px-4 py-3">Market value</th>
                    <th className="px-4 py-3">Unrealized P/L</th>
                    <th className="px-4 py-3">Current</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {alpaca.positions.map((position) => (
                    <tr key={position.symbol}>
                      <td className="px-4 py-3 font-semibold text-white">{position.symbol}</td>
                      <td className="px-4 py-3 text-slate-300">{maybeNumber(position.qty)}</td>
                      <td className="px-4 py-3 text-slate-300">{maybeMoney(position.market_value)}</td>
                      <td className={Number(position.unrealized_pl || 0) >= 0 ? "px-4 py-3 text-emerald-300" : "px-4 py-3 text-rose-300"}>{maybeMoney(position.unrealized_pl)}</td>
                      <td className="px-4 py-3 text-slate-300">{maybeMoney(position.current_price)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {alpaca?.open_orders.length ? (
            <div className="mt-5 overflow-hidden rounded-xl border border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Side</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Qty</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {alpaca.open_orders.map((order) => (
                    <tr key={order.id}>
                      <td className="px-4 py-3 font-semibold text-white">{order.symbol}</td>
                      <td className="px-4 py-3 text-slate-300">{order.side || "Pending"}</td>
                      <td className="px-4 py-3 text-slate-300">{order.type || "Pending"}</td>
                      <td className="px-4 py-3 text-slate-300">{maybeNumber(order.qty ?? order.notional)}</td>
                      <td className="px-4 py-3"><StatusBadge value={order.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}

          {alpaca?.warnings.length ? (
            <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-3">
              {alpaca.warnings.map((warning) => (
                <p key={warning} className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs leading-relaxed text-slate-400">{warning}</p>
              ))}
            </div>
          ) : null}
        </section>
        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading paper validation...</div>
        ) : !data.top_action ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-8 text-center text-sm text-amber-200">
            No source-backed paper candidate is available yet.
          </div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-emerald-500">Paper Candidate</p>
                  <h2 className="mt-1 text-3xl font-black text-white">{data.top_action.symbol} · {data.top_action.action_label}</h2>
                  <p className="mt-2 max-w-4xl text-sm leading-relaxed text-slate-300">{data.top_action.final_reason}</p>
                </div>
                <span className="w-fit rounded-full border border-amber-500 bg-amber-500/10 px-4 py-2 text-sm font-bold uppercase text-amber-300">
                  No live execution
                </span>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-6">
                <MetricCard label="Entry low" value={money(data.top_action.price_plan.buy_zone_low)} accent />
                <MetricCard label="Entry high" value={money(data.top_action.price_plan.buy_zone_high)} />
                <MetricCard label="Stop" value={money(data.top_action.price_plan.stop_loss)} />
                <MetricCard label="Target" value={money(data.top_action.price_plan.target_price)} />
                <MetricCard label="Max risk" value={money(data.top_action.risk_plan.max_dollar_risk)} />
                <MetricCard label="Expected R" value={`${data.top_action.risk_plan.reward_risk_ratio.toFixed(1)}R`} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Paper Trade Checklist</h3>
                <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-300">
                  <li>• Enter only inside the buy zone.</li>
                  <li>• Record actual fill price and time.</li>
                  <li>• Respect the stop and max-dollar-risk plan.</li>
                  <li>• Track whether target hit before stop.</li>
                </ul>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Outcome Labels</h3>
                <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-300">
                  <li>• Target before stop</li>
                  <li>• Stop before target</li>
                  <li>• Timed exit</li>
                  <li>• Invalidated before entry</li>
                </ul>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Learning Loop</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">
                  Paper outcomes should feed the Journal, backtesting labels, and future agent scorecards so the system learns which signals actually produce positive expectancy.
                </p>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Invalidation Rules</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {data.top_action.invalidation_rules.map((rule) => (
                  <div key={rule} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">{rule}</div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
