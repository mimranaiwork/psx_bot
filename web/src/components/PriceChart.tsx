import { useEffect, useRef, useState } from "react";
import {
  createChart,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from "lightweight-charts";
import type { PriceRow } from "../api/client";
import { PALETTE, usePrefersDark } from "../theme";

interface Props {
  rows: PriceRow[];
}

type Overlay = "sma20" | "sma50" | "bollinger";

const OVERLAY_LABELS: Record<Overlay, string> = {
  sma20: "SMA 20",
  sma50: "SMA 50",
  bollinger: "Bollinger Bands",
};

interface LegendItem {
  key: string;
  label: string;
  color: string;
  pane: "price" | "rsi" | "macd";
}

const fmt = (v: number | null | undefined, digits = 2) =>
  v === null || v === undefined ? "–" : v.toFixed(digits);

export default function PriceChart({ rows }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<Record<string, ISeriesApi<"Line" | "Histogram">>>({});
  const dark = usePrefersDark();
  const [overlays, setOverlays] = useState<Record<Overlay, boolean>>({
    sma20: true,
    sma50: true,
    bollinger: false,
  });
  const [legendItems, setLegendItems] = useState<LegendItem[]>([]);
  const [values, setValues] = useState<Record<string, number | null>>({});

  useEffect(() => {
    if (!containerRef.current || rows.length === 0) return;
    const c = dark ? PALETTE.dark : PALETTE.light;
    seriesRef.current = {};
    const items: LegendItem[] = [];

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 520,
      layout: { background: { color: c.surface }, textColor: c.text },
      grid: {
        vertLines: { color: c.grid },
        horzLines: { color: c.grid },
      },
      timeScale: { borderColor: c.baseline },
      rightPriceScale: { borderColor: c.baseline },
      crosshair: { mode: 0 },
    });
    chartRef.current = chart;

    const times = rows.map((r) => r.trade_date.slice(0, 10) as Time);

    // Every series has its axis "last value" badge and price line turned off --
    // with several series sharing a pane those badges stack and overlap. A real
    // HTML legend (below) replaces them, per the dataviz skill's "one tooltip,
    // every series" rule.
    const addLine = (
      key: string,
      label: string,
      pane: LegendItem["pane"],
      paneIndex: number,
      color: string,
      values: (number | null)[],
      extra: Record<string, unknown> = {}
    ) => {
      const s = chart.addSeries(
        LineSeries,
        { color, lineWidth: 1, lastValueVisible: false, priceLineVisible: false, ...extra },
        paneIndex
      );
      s.setData(
        rows
          .map((_, i) => ({ time: times[i], value: values[i] }))
          .filter((d): d is { time: Time; value: number } => d.value !== null)
      );
      seriesRef.current[key] = s;
      items.push({ key, label, color, pane });
      return s;
    };

    // --- main pane: close price + toggleable overlays -------------------
    addLine("close", "Close", "price", 0, c.series1, rows.map((r) => r.close), { lineWidth: 2 });

    if (overlays.sma20) {
      addLine("sma20", "SMA 20", "price", 0, c.series3, rows.map((r) => r.sma_20));
    }
    if (overlays.sma50) {
      addLine("sma50", "SMA 50", "price", 0, c.series2, rows.map((r) => r.sma_50));
    }
    if (overlays.bollinger) {
      addLine("bbUpper", "BB Upper", "price", 0, c.seq150, rows.map((r) => r.bb_upper), { lineStyle: 2 });
      addLine("bbLower", "BB Lower", "price", 0, c.seq150, rows.map((r) => r.bb_lower), { lineStyle: 2 });
    }

    // --- RSI pane ---------------------------------------------------------
    const rsiSeries = addLine("rsi", "RSI 14", "rsi", 1, c.series1, rows.map((r) => r.rsi_14));
    rsiSeries.createPriceLine({ price: 70, color: c.textMuted, lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });
    rsiSeries.createPriceLine({ price: 30, color: c.textMuted, lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: "" });

    // --- MACD pane ----------------------------------------------------------
    addLine("macd", "MACD", "macd", 2, c.series1, rows.map((r) => r.macd));
    addLine("macdSignal", "Signal", "macd", 2, c.series6, rows.map((r) => r.macd_signal));

    const histSeries = chart.addSeries(
      HistogramSeries,
      { lastValueVisible: false, priceLineVisible: false },
      2
    );
    histSeries.setData(
      rows
        .map((r, i) => ({
          time: times[i],
          value: r.macd_hist,
          color: (r.macd_hist ?? 0) >= 0 ? c.series1 : c.series6,
        }))
        .filter((d) => d.value !== null) as { time: Time; value: number; color: string }[]
    );
    seriesRef.current.macdHist = histSeries;
    items.push({ key: "macdHist", label: "Histogram", color: c.textMuted, pane: "macd" });

    setLegendItems(items);

    // Seed the legend with the latest values, then live-update on hover.
    const lastIdx = rows.length - 1;
    const seedValues: Record<string, number | null> = {
      close: rows[lastIdx].close,
      sma20: rows[lastIdx].sma_20,
      sma50: rows[lastIdx].sma_50,
      bbUpper: rows[lastIdx].bb_upper,
      bbLower: rows[lastIdx].bb_lower,
      rsi: rows[lastIdx].rsi_14,
      macd: rows[lastIdx].macd,
      macdSignal: rows[lastIdx].macd_signal,
      macdHist: rows[lastIdx].macd_hist,
    };
    setValues(seedValues);

    chart.subscribeCrosshairMove((param) => {
      if (!param.time) {
        setValues(seedValues);
        return;
      }
      const next: Record<string, number | null> = {};
      for (const [key, series] of Object.entries(seriesRef.current)) {
        const point = param.seriesData.get(series) as { value?: number } | undefined;
        next[key] = point?.value ?? null;
      }
      setValues(next);
    });

    chart.timeScale().fitContent();

    const resize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      chart.remove();
      chartRef.current = null;
    };
  }, [rows, dark, overlays]);

  const renderLegendRow = (pane: LegendItem["pane"], title: string) => {
    const paneItems = legendItems.filter((item) => item.pane === pane);
    if (paneItems.length === 0) return null;
    return (
      <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 12, flexWrap: "wrap" }}>
        <span style={{ color: "var(--text-muted)", minWidth: 40 }}>{title}</span>
        {paneItems.map((item) => (
          <span key={item.key} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
            <span
              aria-hidden="true"
              style={{ display: "inline-block", width: 12, height: 2, background: item.color }}
            />
            <span style={{ color: "var(--text-secondary)" }}>{item.label}</span>
            <strong style={{ color: "var(--text-primary)", fontVariantNumeric: "tabular-nums" }}>
              {fmt(values[item.key])}
            </strong>
          </span>
        ))}
      </div>
    );
  };

  return (
    <div>
      <div style={{ display: "flex", gap: 16, marginBottom: 8, fontSize: 13 }}>
        {(Object.keys(OVERLAY_LABELS) as Overlay[]).map((key) => (
          <label key={key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <input
              type="checkbox"
              checked={overlays[key]}
              onChange={(e) =>
                setOverlays((prev) => ({ ...prev, [key]: e.target.checked }))
              }
            />
            {OVERLAY_LABELS[key]}
          </label>
        ))}
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 4,
          padding: "6px 8px",
          border: "1px solid var(--border)",
          borderBottom: "none",
          borderRadius: "6px 6px 0 0",
          background: "var(--surface-1)",
        }}
      >
        {renderLegendRow("price", "Price")}
        {renderLegendRow("rsi", "RSI")}
        {renderLegendRow("macd", "MACD")}
      </div>
      <div ref={containerRef} style={{ border: "1px solid var(--border)", borderRadius: "0 0 6px 6px" }} />
    </div>
  );
}
