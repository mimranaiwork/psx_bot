export default function DisclaimerBanner() {
  return (
    <div
      style={{
        background: "var(--surface-1)",
        borderBottom: "1px solid var(--border)",
        padding: "8px 16px",
        fontSize: 13,
        color: "var(--text-secondary)",
      }}
    >
      Decision support only, not a guarantee — every signal is probability-weighted and a
      human must confirm any trade. Price/fundamentals/news data is sourced from Yahoo Finance,
      unofficial and unverified for PSX equities, unless loaded from a licensed CSV. Paper-trade
      for 3–6 months before using real capital.
    </div>
  );
}
