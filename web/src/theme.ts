import { useEffect, useState } from "react";

export const PALETTE = {
  light: {
    surface: "#fcfcfb",
    text: "#0b0b0b",
    textMuted: "#898781",
    grid: "#e1e0d9",
    baseline: "#c3c2b7",
    series1: "#2a78d6",
    series2: "#1baf7a",
    series3: "#eda100",
    series6: "#e34948",
    seq150: "#b7d3f6",
  },
  dark: {
    surface: "#1a1a19",
    text: "#ffffff",
    textMuted: "#898781",
    grid: "#2c2c2a",
    baseline: "#383835",
    series1: "#3987e5",
    series2: "#199e70",
    series3: "#c98500",
    series6: "#e66767",
    seq150: "#184f95",
  },
};

export function usePrefersDark() {
  const [dark, setDark] = useState(
    () => window.matchMedia("(prefers-color-scheme: dark)").matches
  );
  useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = (e: MediaQueryListEvent) => setDark(e.matches);
    mql.addEventListener("change", listener);
    return () => mql.removeEventListener("change", listener);
  }, []);
  return dark;
}
