import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, type BacktestRun } from "../api/client";

type SortKey = keyof Pick<
  BacktestRun,
  "strategy_return" | "baseline_return" | "sharpe_ratio" | "win_rate" | "max_drawdown"
>;

export default function BacktestsPage() {
  const backtestsQuery = useQuery({ queryKey: ["backtests", "all"], queryFn: () => api.backtests() });
  const [sortKey, setSortKey] = useState<SortKey>("strategy_return");

  const sorted = useMemo(() => {
    const rows = backtestsQuery.data ?? [];
    return [...rows].sort((a, b) => (b[sortKey] ?? -Infinity) - (a[sortKey] ?? -Infinity));
  }, [backtestsQuery.data, sortKey]);

  const sortableColumns: { key: SortKey; label: string }[] = [
    { key: "strategy_return", label: "Strategy return" },
    { key: "baseline_return", label: "Buy & hold return" },
    { key: "sharpe_ratio", label: "Sharpe" },
    { key: "win_rate", label: "Win rate" },
    { key: "max_drawdown", label: "Max drawdown" },
  ];

  return (
    <div>
      <h1 style={{ fontSize: 20 }}>Backtest results ({sorted.length} runs)</h1>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            {sortableColumns.map((c) => (
              <th key={c.key}>
                <button
                  onClick={() => setSortKey(c.key)}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    font: "inherit",
                    color: sortKey === c.key ? "var(--series-1)" : "inherit",
                    fontWeight: sortKey === c.key ? 700 : 600,
                  }}
                >
                  {c.label} {sortKey === c.key ? "▾" : ""}
                </button>
              </th>
            ))}
            <th>Beats B&H</th>
            <th>Trades</th>
            <th>Run date</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => {
            const beats = (r.strategy_return ?? -Infinity) > (r.baseline_return ?? Infinity);
            return (
              <tr key={r.id}>
                <td>{r.symbol}</td>
                <td>{r.strategy_return !== null ? `${(r.strategy_return * 100).toFixed(1)}%` : "—"}</td>
                <td>{r.baseline_return !== null ? `${(r.baseline_return * 100).toFixed(1)}%` : "—"}</td>
                <td>{r.sharpe_ratio ?? "—"}</td>
                <td>{r.win_rate ?? "—"}</td>
                <td>{r.max_drawdown !== null ? `${(r.max_drawdown * 100).toFixed(1)}%` : "—"}</td>
                <td style={{ color: beats ? "var(--status-good)" : "var(--status-critical)" }}>
                  {beats ? "✓" : "✗"}
                </td>
                <td>{r.total_trades}</td>
                <td>{r.run_date?.slice(0, 10)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
