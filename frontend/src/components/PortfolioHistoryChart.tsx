"use client";

import { useEffect, useMemo, useRef } from "react";
import { createChart, ColorType, type IChartApi, type ISeriesApi, type UTCTimestamp, LineSeries } from "lightweight-charts";
import type { AlpacaPaperPortfolioHistory } from "@/lib/api";

type Point = { time: UTCTimestamp; value: number };

function toSeries(history: AlpacaPaperPortfolioHistory | null): Point[] {
  if (!history?.timestamps?.length || !history?.equity?.length) return [];
  const len = Math.min(history.timestamps.length, history.equity.length);
  const points: Point[] = [];
  for (let i = 0; i < len; i += 1) {
    const ts = history.timestamps[i];
    const eq = history.equity[i];
    if (!Number.isFinite(ts) || !Number.isFinite(eq)) continue;
    points.push({ time: ts as UTCTimestamp, value: eq });
  }
  return points;
}

export function PortfolioHistoryChart({
  history,
  accent = "rgba(16,185,129,0.75)",
  height = 320,
}: {
  history: AlpacaPaperPortfolioHistory | null;
  accent?: string;
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  const data = useMemo(() => toSeries(history), [history]);

  useEffect(() => {
    if (!containerRef.current || chartRef.current) return;

    const chart = createChart(containerRef.current, {
      height,
      layout: {
        background: { type: ColorType.Solid, color: "rgba(0,0,0,0)" },
        textColor: "#cbd5e1",
      },
      grid: {
        vertLines: { color: "rgba(16,185,129,0.10)" },
        horzLines: { color: "rgba(16,185,129,0.10)" },
      },
      rightPriceScale: { borderColor: "rgba(16,185,129,0.15)" },
      timeScale: { borderColor: "rgba(16,185,129,0.15)", timeVisible: true },
      crosshair: { vertLine: { color: "rgba(16,185,129,0.18)" }, horzLine: { color: "rgba(16,185,129,0.18)" } },
    });

    const series = chart.addSeries(LineSeries, {
      color: accent,
      lineWidth: 2,
      ...( { lineType: 2 } as any ), // try curved line if runtime supports
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth });
    };
    handleResize();
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [accent, height]);

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    seriesRef.current.setData(data);
    chartRef.current.timeScale().fitContent();
  }, [data]);

  if (!history) {
    return <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 text-sm text-slate-400">Loading portfolio history…</div>;
  }

  if (history.status !== "connected" || data.length === 0) {
    return (
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
        {history.message || "Portfolio history unavailable."}
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-2 shadow-[0_0_40px_rgba(0,0,0,0.18)] backdrop-blur">
      <div ref={containerRef} className="w-full" />
      <div className="px-3 pb-2 pt-1 text-[11px] text-slate-500">
        Period: <span className="font-mono text-slate-300">{history.period}</span> · Timeframe:{" "}
        <span className="font-mono text-slate-300">{history.timeframe}</span>
      </div>
    </div>
  );
}

