import type { SignalRecord } from "../api/client";
import SignalBadge from "./SignalBadge";

export default function SignalCard({ signal }: { signal: SignalRecord }) {
  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 6, padding: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 8 }}>
        <SignalBadge signal={signal.signal} />
        <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
          {signal.confidence} confidence · {signal.signal_date}
        </span>
      </div>
      {signal.model_probability !== null && (
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0" }}>
          Model probability: {(signal.model_probability * 100).toFixed(0)}%
        </p>
      )}
      {signal.fundamental_flag && (
        <p style={{ fontSize: 13, color: "var(--text-secondary)", margin: "4px 0" }}>
          Fundamental flag: {signal.fundamental_flag}
        </p>
      )}
      {signal.rationale && (
        <pre
          style={{
            whiteSpace: "pre-wrap",
            fontFamily: "inherit",
            fontSize: 13,
            marginTop: 8,
            color: "var(--text-primary)",
          }}
        >
          {signal.rationale}
        </pre>
      )}
      {signal.actual_forward_return !== null && (
        <p style={{ fontSize: 13, marginTop: 8 }}>
          Actual forward return: {(signal.actual_forward_return * 100).toFixed(1)}%{" "}
          {signal.outcome_correct === 1 ? "✓ correct" : signal.outcome_correct === 0 ? "✗ incorrect" : ""}
        </p>
      )}
    </div>
  );
}
