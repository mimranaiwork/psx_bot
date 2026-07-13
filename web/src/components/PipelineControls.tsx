import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../api/client";

interface Props {
  symbol: string;
}

export default function PipelineControls({ symbol }: Props) {
  const queryClient = useQueryClient();
  const [yfTicker, setYfTicker] = useState(`${symbol}.KA`);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["prices", symbol] });
    queryClient.invalidateQueries({ queryKey: ["signal", symbol] });
    queryClient.invalidateQueries({ queryKey: ["backtests", symbol] });
    queryClient.invalidateQueries({ queryKey: ["signals-log", symbol] });
    queryClient.invalidateQueries({ queryKey: ["symbols"] });
  };

  const run = (label: string, fn: () => Promise<{ detail: string }>) =>
    useMutation({
      mutationFn: fn,
      onSuccess: (res) => {
        setError(null);
        setMessage(`${label}: ${res.detail}`);
        invalidateAll();
      },
      onError: (e) => {
        setMessage(null);
        setError(e instanceof ApiError ? e.message : `${label} failed.`);
      },
    });

  const loadPrices = run("Load prices", () => api.loadPrices(symbol, yfTicker));
  const loadFundamentals = run("Load fundamentals", () => api.loadFundamentals(symbol, yfTicker));
  const loadNews = run("Load news", () => api.loadNews(symbol, yfTicker));
  const train = run("Train", () => api.train(symbol));
  const backtest = run("Backtest", () => api.backtest(symbol));
  const generateSignal = run("Signal", () => api.generateSignal(symbol));
  const updateOutcomes = run("Update outcomes", () => api.updateOutcomes(symbol));

  const mutations = [
    ["Load Prices (Yahoo)", loadPrices],
    ["Load Fundamentals", loadFundamentals],
    ["Load News", loadNews],
    ["Train Model", train],
    ["Run Backtest", backtest],
    ["Generate Signal", generateSignal],
    ["Update Outcomes", updateOutcomes],
  ] as const;

  const anyPending = mutations.some(([, m]) => m.isPending);

  return (
    <div style={{ border: "1px solid var(--border)", borderRadius: 6, padding: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <label style={{ fontSize: 13, color: "var(--text-secondary)" }}>Yahoo ticker:</label>
        <input
          value={yfTicker}
          onChange={(e) => setYfTicker(e.target.value)}
          style={{ padding: "4px 8px", border: "1px solid var(--border)", borderRadius: 4 }}
        />
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
        {mutations.map(([label, m]) => (
          <button
            key={label}
            disabled={anyPending}
            onClick={() => m.mutate()}
            style={{
              padding: "6px 12px",
              borderRadius: 4,
              border: "1px solid var(--border)",
              background: m.isPending ? "var(--surface-2)" : "var(--surface-1)",
              opacity: anyPending && !m.isPending ? 0.5 : 1,
            }}
          >
            {m.isPending ? `${label}...` : label}
          </button>
        ))}
      </div>
      {message && <p style={{ color: "var(--status-good)", fontSize: 13, marginTop: 8 }}>{message}</p>}
      {error && <p style={{ color: "var(--status-critical)", fontSize: 13, marginTop: 8 }}>{error}</p>}
    </div>
  );
}
