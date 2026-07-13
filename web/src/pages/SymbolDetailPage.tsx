import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import PriceChart from "../components/PriceChart";
import SignalCard from "../components/SignalCard";
import PipelineControls from "../components/PipelineControls";

export default function SymbolDetailPage() {
  const { symbol = "" } = useParams();

  const pricesQuery = useQuery({
    queryKey: ["prices", symbol],
    queryFn: () => api.getPrices(symbol),
  });
  const signalQuery = useQuery({
    queryKey: ["signal", symbol],
    queryFn: () => api.latestSignalFor(symbol),
    retry: false,
  });
  const backtestsQuery = useQuery({
    queryKey: ["backtests", symbol],
    queryFn: () => api.backtests(symbol),
  });

  const latestBacktest = backtestsQuery.data?.[0];

  return (
    <div>
      <p>
        <Link to="/">← All symbols</Link>
      </p>
      <h1 style={{ fontSize: 24 }}>{symbol}</h1>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, alignItems: "start" }}>
        <div>
          {pricesQuery.isLoading && <p>Loading price history...</p>}
          {pricesQuery.isError && <p>No price history loaded for {symbol} yet.</p>}
          {pricesQuery.data && pricesQuery.data.length > 0 && <PriceChart rows={pricesQuery.data} />}
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <h2 style={{ fontSize: 16 }}>Current signal</h2>
            {signalQuery.isLoading && <p>Loading...</p>}
            {signalQuery.isError && <p>No signal generated yet for {symbol}.</p>}
            {signalQuery.data && <SignalCard signal={signalQuery.data} />}
          </div>

          {latestBacktest && (
            <div>
              <h2 style={{ fontSize: 16 }}>Latest backtest</h2>
              <div style={{ border: "1px solid var(--border)", borderRadius: 6, padding: 12, fontSize: 13 }}>
                <p>
                  Strategy: {(latestBacktest.strategy_return! * 100).toFixed(1)}% vs. buy-hold:{" "}
                  {(latestBacktest.baseline_return! * 100).toFixed(1)}%
                </p>
                <p>Sharpe: {latestBacktest.sharpe_ratio} · Win rate: {latestBacktest.win_rate}</p>
                <p>Max drawdown: {(latestBacktest.max_drawdown! * 100).toFixed(1)}% · Trades: {latestBacktest.total_trades}</p>
              </div>
            </div>
          )}

          <div>
            <h2 style={{ fontSize: 16 }}>Pipeline controls</h2>
            <PipelineControls symbol={symbol} />
          </div>
        </div>
      </div>
    </div>
  );
}
