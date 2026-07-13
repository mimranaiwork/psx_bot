import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import SignalBadge from "../components/SignalBadge";

export default function AccuracyLogPage() {
  const [symbolFilter, setSymbolFilter] = useState("");
  const logQuery = useQuery({
    queryKey: ["signals-log", symbolFilter || undefined],
    queryFn: () => api.signalsLog(symbolFilter || undefined),
  });

  const rows = logQuery.data ?? [];
  const scored = rows.filter((r) => r.outcome_correct !== null);
  const accuracy = scored.length
    ? scored.filter((r) => r.outcome_correct === 1).length / scored.length
    : null;

  return (
    <div>
      <h1 style={{ fontSize: 20 }}>Signal accuracy log</h1>
      <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "12px 0" }}>
        <input
          placeholder="Filter by symbol..."
          value={symbolFilter}
          onChange={(e) => setSymbolFilter(e.target.value.toUpperCase())}
          style={{ padding: "6px 10px", border: "1px solid var(--border)", borderRadius: 4 }}
        />
        {accuracy !== null && (
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            Scored outcomes: {scored.length} · Directional accuracy: {(accuracy * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Date</th>
            <th>Signal</th>
            <th>Confidence</th>
            <th>Fundamental</th>
            <th>Forward return</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.symbol}</td>
              <td>{r.signal_date}</td>
              <td>
                <SignalBadge signal={r.signal} />
              </td>
              <td>{r.confidence}</td>
              <td>{r.fundamental_flag}</td>
              <td>{r.actual_forward_return !== null ? `${(r.actual_forward_return * 100).toFixed(1)}%` : "—"}</td>
              <td>
                {r.outcome_correct === 1 ? "✓" : r.outcome_correct === 0 ? "✗" : "pending"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
