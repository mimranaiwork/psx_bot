import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";

function CheckMark({ ok }: { ok?: boolean }) {
  return (
    <span style={{ color: ok ? "var(--status-good)" : "var(--text-muted)" }}>
      {ok ? "✓" : "—"}
    </span>
  );
}

export default function BreakoutScreenerPage() {
  const screenerQuery = useQuery({
    queryKey: ["screener", "breakouts"],
    queryFn: () => api.breakoutScreener(true),
  });

  const candidates = screenerQuery.data ?? [];

  return (
    <div>
      <h1 style={{ fontSize: 20 }}>Pre-breakout screener</h1>
      <p style={{ fontSize: 13, color: "var(--text-secondary)", maxWidth: 640 }}>
        Rule-based pattern match: tight Bollinger Band consolidation ("squeeze") near a
        recent high, with volume starting to build and momentum not yet overextended.
        This flags a technical <em>setup</em>, not a prediction — it does not mean a
        breakout will actually follow.
      </p>

      {screenerQuery.isLoading && <p>Scanning all loaded symbols...</p>}
      {screenerQuery.isError && <p>Failed to load screener results.</p>}
      {!screenerQuery.isLoading && candidates.length === 0 && (
        <p>No pre-breakout setups found among currently loaded symbols.</p>
      )}

      {candidates.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Checks</th>
              <th>Close</th>
              <th>Below high</th>
              <th>RSI 14</th>
              <th>Vol ratio</th>
              <th>Squeeze</th>
              <th>Near resistance</th>
              <th>Volume building</th>
              <th>Momentum ok</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((c) => (
              <tr key={c.symbol}>
                <td>
                  <Link to={`/symbols/${c.symbol}`}>{c.symbol}</Link>
                </td>
                <td>{c.checks_passed}/4</td>
                <td>{c.close?.toFixed(2)}</td>
                <td>{c.pct_from_high !== undefined ? `${(c.pct_from_high * 100).toFixed(1)}%` : "—"}</td>
                <td>{c.rsi_14?.toFixed(1)}</td>
                <td>{c.volume_spike_ratio?.toFixed(2)}</td>
                <td>
                  <CheckMark ok={c.squeeze} />
                </td>
                <td>
                  <CheckMark ok={c.near_resistance} />
                </td>
                <td>
                  <CheckMark ok={c.volume_building} />
                </td>
                <td>
                  <CheckMark ok={c.momentum_ok} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
