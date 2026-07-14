import { NavLink, Route, Routes } from "react-router-dom";
import DisclaimerBanner from "./components/DisclaimerBanner";
import SymbolListPage from "./pages/SymbolListPage";
import SymbolDetailPage from "./pages/SymbolDetailPage";
import AccuracyLogPage from "./pages/AccuracyLogPage";
import BacktestsPage from "./pages/BacktestsPage";
import BreakoutScreenerPage from "./pages/BreakoutScreenerPage";

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  color: isActive ? "var(--series-1)" : "var(--text-primary)",
  fontWeight: isActive ? 700 : 400,
  textDecoration: "none",
});

function App() {
  return (
    <>
      <DisclaimerBanner />
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 24,
          padding: "12px 16px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <strong>PSX AI Insights Bot</strong>
        <nav style={{ display: "flex", gap: 16, fontSize: 14 }}>
          <NavLink to="/" end style={navLinkStyle}>
            Symbols
          </NavLink>
          <NavLink to="/backtests" style={navLinkStyle}>
            Backtests
          </NavLink>
          <NavLink to="/signals-log" style={navLinkStyle}>
            Accuracy Log
          </NavLink>
          <NavLink to="/breakouts" style={navLinkStyle}>
            Breakout Screener
          </NavLink>
        </nav>
      </header>

      <main style={{ padding: 16, flex: 1 }}>
        <Routes>
          <Route path="/" element={<SymbolListPage />} />
          <Route path="/symbols/:symbol" element={<SymbolDetailPage />} />
          <Route path="/backtests" element={<BacktestsPage />} />
          <Route path="/signals-log" element={<AccuracyLogPage />} />
          <Route path="/breakouts" element={<BreakoutScreenerPage />} />
        </Routes>
      </main>
    </>
  );
}

export default App;
