import type { SignalName } from "../api/client";

const STATUS: Record<SignalName, { color: string; icon: string }> = {
  BUY: { color: "var(--status-good)", icon: "▲" },
  HOLD: { color: "var(--status-warning)", icon: "●" },
  SELL: { color: "var(--status-critical)", icon: "▼" },
};

export default function SignalBadge({ signal }: { signal: SignalName }) {
  const { color, icon } = STATUS[signal];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
        fontWeight: 700,
        color,
        border: `1px solid ${color}`,
      }}
    >
      <span aria-hidden="true">{icon}</span>
      {signal}
    </span>
  );
}
