import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import SignalBadge from "../components/SignalBadge";

export default function SymbolListPage() {
  const symbolsQuery = useQuery({ queryKey: ["symbols"], queryFn: api.listSymbols });
  const signalsQuery = useQuery({ queryKey: ["signals", "latest"], queryFn: api.latestSignals });

  if (symbolsQuery.isLoading) return <p>Loading symbols...</p>;
  if (symbolsQuery.isError) return <p>Failed to load symbols.</p>;

  const signalBySymbol = new Map((signalsQuery.data ?? []).map((s) => [s.symbol, s]));

  return (
    <div>
      <h1 style={{ fontSize: 20 }}>Symbols ({symbolsQuery.data?.length ?? 0})</h1>
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Rows</th>
            <th>Latest date</th>
            <th>Signal</th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {symbolsQuery.data?.map((s) => {
            const sig = signalBySymbol.get(s.symbol);
            return (
              <tr key={s.symbol}>
                <td>
                  <Link to={`/symbols/${s.symbol}`}>{s.symbol}</Link>
                </td>
                <td>{s.row_count}</td>
                <td>{s.latest_date}</td>
                <td>{sig ? <SignalBadge signal={sig.signal} /> : "—"}</td>
                <td>{sig?.confidence ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
