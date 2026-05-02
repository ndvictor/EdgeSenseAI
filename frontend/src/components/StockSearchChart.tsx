"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, ColorType, type IChartApi, type ISeriesApi, type UTCTimestamp, CandlestickSeries, LineSeries } from "lightweight-charts";
import { api, type MarketDataSnapshot, type MarketDataSource, type PriceHistory } from "@/lib/api";

const QUICK_SYMBOLS = ["AMD", "NVDA", "AAPL", "MSFT", "TSLA", "META", "GOOGL", "BTC-USD"];

type ChartMode = "line" | "candles";

type CandlePoint = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

type LinePoint = {
  time: UTCTimestamp;
  value: number;
};

function toCandleData(response: PriceHistory): CandlePoint[] {
  return response.data
    .filter((candle) => candle.open !== null && candle.high !== null && candle.low !== null && candle.close !== null)
    .map((candle) => ({
      time: Math.floor(new Date(candle.date).getTime() / 1000) as UTCTimestamp,
      open: Number(candle.open),
      high: Number(candle.high),
      low: Number(candle.low),
      close: Number(candle.close),
    }));
}

function toLineData(response: PriceHistory): LinePoint[] {
  return response.data
    .filter((candle) => candle.close !== null)
    .map((candle) => ({
      time: Math.floor(new Date(candle.date).getTime() / 1000) as UTCTimestamp,
      value: Number(candle.close),
    }));
}

function money(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function formatPercent(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toFixed(2)}%`;
}

export function StockSearchChart() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const lineSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const [symbol, setSymbol] = useState("AMD");
  const [dataSource, setDataSource] = useState<MarketDataSource>("auto");
  const [chartMode, setChartMode] = useState<ChartMode>("line");
  const [period, setPeriod] = useState("1mo");
  const [interval, setIntervalValue] = useState("1d");
  const [snapshot, setSnapshot] = useState<MarketDataSnapshot | null>(null);
  const [history, setHistory] = useState<PriceHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const candleData = useMemo(() => (history ? toCandleData(history) : []), [history]);
  const lineData = useMemo(() => (history ? toLineData(history) : []), [history]);

  async function load(nextSymbol = symbol) {
    const normalizedSymbol = nextSymbol.trim().toUpperCase();
    if (!normalizedSymbol) return;
    setLoading(true);
    setError(null);
    try {
      const [nextSnapshot, nextHistory] = await Promise.all([
        api.getMarketDataSnapshot(normalizedSymbol, dataSource),
        api.getMarketDataHistory(normalizedSymbol, period, interval, dataSource),
      ]);
      setSymbol(normalizedSymbol);
      setSnapshot(nextSnapshot);
      setHistory(nextHistory);
      if (nextSnapshot.data_quality === "unavailable" || nextHistory.data_quality === "unavailable" || nextHistory.data.length === 0) {
        setError(nextSnapshot.error || nextHistory.error || `No market data returned for ${normalizedSymbol}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load market chart. Confirm backend is running on port 8900 and NEXT_PUBLIC_API_URL points to it.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      height: 420,
      layout: {
        background: { type: ColorType.Solid, color: "#020617" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "#1e293b" },
        horzLines: { color: "#1e293b" },
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
      timeScale: {
        borderColor: "#334155",
        timeVisible: true,
      },
    });

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
      visible: false,
    });
    const lineSeries = chart.addSeries(LineSeries, {
      color: "#22c55e",
      lineWidth: 2,
      visible: true,
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    lineSeriesRef.current = lineSeries;

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    handleResize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      lineSeriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !lineSeriesRef.current) return;
    candleSeriesRef.current.setData(candleData);
    lineSeriesRef.current.setData(lineData);
    candleSeriesRef.current.applyOptions({ visible: chartMode === "candles" });
    lineSeriesRef.current.applyOptions({ visible: chartMode === "line" });
    chartRef.current.timeScale().fitContent();
  }, [candleData, lineData, chartMode]);

  useEffect(() => {
    load(symbol);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataSource, period, interval]);

  return (
    <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-500">Live market chart</p>
          <h2 className="mt-1 text-2xl font-black text-white">Search ticker and visualize price action</h2>
          <p className="mt-2 max-w-4xl text-sm leading-relaxed text-slate-400">
            Uses the migrated TradeSense-style market data route: /api/market-data/history. Choose Line or Candlestick view.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-6 xl:min-w-[900px]">
          <label className="md:col-span-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Ticker</span>
            <input
              value={symbol}
              onChange={(event) => setSymbol(event.target.value.toUpperCase())}
              onKeyDown={(event) => {
                if (event.key === "Enter") load(symbol);
              }}
              className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-sm font-bold text-white"
              placeholder="Search ticker, e.g. AAPL"
            />
          </label>
          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Data Source</span>
            <select value={dataSource} onChange={(event) => setDataSource(event.target.value as MarketDataSource)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-3 py-3 text-sm text-white">
              <option value="auto">Auto</option>
              <option value="yfinance">YFinance</option>
              <option value="alpaca">Alpaca</option>
              <option value="mock">Mock</option>
            </select>
          </label>
          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Chart</span>
            <select value={chartMode} onChange={(event) => setChartMode(event.target.value as ChartMode)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-3 py-3 text-sm text-white">
              <option value="line">Line</option>
              <option value="candles">Candlestick</option>
            </select>
          </label>
          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Period</span>
            <select value={period} onChange={(event) => setPeriod(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-3 py-3 text-sm text-white">
              <option value="5d">5D</option>
              <option value="1mo">1M</option>
              <option value="3mo">3M</option>
              <option value="6mo">6M</option>
              <option value="1y">1Y</option>
            </select>
          </label>
          <label>
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Interval</span>
            <select value={interval} onChange={(event) => setIntervalValue(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-3 py-3 text-sm text-white">
              <option value="1d">1D</option>
              <option value="1h">1H</option>
              <option value="15m">15M</option>
              <option value="5m">5M</option>
            </select>
          </label>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {QUICK_SYMBOLS.map((item) => (
          <button key={item} onClick={() => load(item)} className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-bold text-slate-300 hover:border-emerald-500 hover:text-emerald-300">
            {item}
          </button>
        ))}
        <button onClick={() => load(symbol)} disabled={loading} className="rounded-full bg-emerald-600 px-4 py-1 text-xs font-black text-slate-950 disabled:cursor-not-allowed disabled:opacity-60">
          {loading ? "Loading..." : "Search"}
        </button>
      </div>

      {error && <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

      {snapshot && (
        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-6">
          <Metric label="Price" value={money(snapshot.price)} />
          <Metric label="Change" value={formatPercent(snapshot.change_percent)} />
          <Metric label="Volume" value={snapshot.volume ? snapshot.volume.toLocaleString() : "—"} />
          <Metric label="Spread" value={formatPercent(snapshot.bid_ask_spread)} />
          <Metric label="Provider" value={snapshot.provider ?? "—"} />
          <Metric label="Quality" value={snapshot.data_quality ?? "—"} />
        </div>
      )}

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-2">
        <div ref={containerRef} className="h-[420px] w-full" />
        {history && history.data.length === 0 && (
          <div className="px-4 pb-4 text-sm text-slate-400">No chart data returned for the selected source. Choose Mock only for explicit offline testing, or configure Alpaca/Polygon for reliable live data.</div>
        )}
      </div>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 truncate text-sm font-black text-white">{value}</p>
    </div>
  );
}
