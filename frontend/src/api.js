import { API_URL } from "./config.js";

export async function getJson(path, params = {}, signal) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_URL}${path}${qs ? `?${qs}` : ""}`, { signal });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

export const fmtMw = (n, digits = 0) =>
  n == null ? "–" : `${Number(n).toLocaleString("en-GB", { maximumFractionDigits: digits })} MW`;

export const fmtSigned = (n) =>
  n == null ? "–" : `${n > 0 ? "+" : ""}${Number(n).toLocaleString("en-GB", { maximumFractionDigits: 0 })} MW`;
