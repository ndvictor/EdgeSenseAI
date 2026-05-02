"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { createChart, ColorType, type IChartApi, type ISeriesApi, type UTCTimestamp, CandlestickSeries } from "lightweight-charts";
import { api, type MarketCandlesResponse, type MarketSnapshot } from "@/lib/api";

const QUICK_SYMBOLS = ["AMD", "NVDA", "AAPL", "MSFT", "TSLA", "META", "GOOGL", "BTC-USD"];

type ChartPoint = {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
};

function toChartData(response: MarketCandlesResponse): ChartPoint[] {
  return response.candles.map((candle) => ({
    time: Math.floor(new Date(candle.time).getTime() / 1000) as UTCTimestamp,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  }));
}

function money(value?: number) {
  if (value === undefined || Number.isNaN(value)) return "—";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function StockSearchChart() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const [symbol, setSymbol] = useState("AMD");
  const [provider, setProvider] = useState<"mock" | "yfinance">("yfinance");
  const [period, setPeriod] = useState("1mo");
  const [interval, setIntervalValue] = useState("1d");
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [candles, setCandles] = useState<MarketCandlesResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chartData = useMemo(() => (candles ? toChartData(candles) : []), [candles]);

  async function load(nextSymbol = symbol) {
    const normalizedSymbol = nextSymbol.trim().toUpperCase();
    if (!normalizedSymbol) return;
    setLoading(true);
    setError(null);
    try {
      const [nextSnapshot, nextCandles] = await Promise.all([
        api.getMarketSnapshot(normalizedSymbol, provider),
        api.getMarketCandles(normalizedSymbol, provider, period, interval),
      ]);
      setSymbol(normalizedSymbol);
      setSnapshot(nextSnapshot);
      setCandles(nextCandles);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load market chart");
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

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#22c55e",
      downColor: "#ef4444",
      borderUpColor: "#22c55e",
      borderDownColor: "#ef4444",
      wickUpColor: "#22c55e",
      wickDownColor: "#ef4444",
    });

    chartRef.current = chart;
    seriesRef.current = series;

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
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current || chartData.length === 0) return;
    seriesRef.current.setData(chartData);
    chartRef.current.timeScale().fitContent();
  }, [chartData]);

  useEffect(() => {
    load("AMD");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [provider, period, interval]);

  return (
    <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-500">Live market chart</p>
          <h2 className="mt-1 text-2xl font-black text-white">Search ticker and visualize price action</h2>
          <p className="mt-2 max-w-4xl text-sm leading-relaxed text-slate-400">
            Use yfinance for research-grade live/recent data or mock for offline testing. This chart is for data visualization and feature workflow validation, not direct execution.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-3 md:grid-cols-5 xl:min-w-[760px]">
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
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">Provider</span>
            <select value={provider} onChange={(event) => setProvider(event.target.value as "mock" | "yfinance")} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-3 py-3 text-sm text-white">
              <option value="yfinance">YFinance</option>
              <option value="mock">Mock</option>
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
          <Metric label="Price" value={money(snapshot.current_price)} />
          <Metric label="Change" value={`${snapshot.day_change_percent.toFixed(2)}%`} />
          <Metric label="Volume" value={snapshot.volume.toLocaleString()} />
          <Metric label="RVOL" value={`${snapshot.relative_volume.toFixed(2)}x`} />
          <Metric label="Spread" value={`${snapshot.spread_percent.toFixed(3)}%`} />
          <Metric label="Mode" value={snapshot.data_mode.replace(/_/g, " ")} />
        </div>
      )}

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-2">
        <div ref={containerRef} className="h-[420px] w-full" />
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
