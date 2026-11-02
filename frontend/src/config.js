export const API_URL = import.meta.env.VITE_API_URL || "";

// January 2026 only (challenge scope).
export const MIN_DATE = "2026-01-01";
export const MAX_DATE = "2026-01-31";
export const DEFAULT_DATE = "2026-01-15";

// Day-ahead decision cutoff, as a time on the day BEFORE delivery.
// TODO: confirm the real gate time with the client; backend receives it as HH:MM.
export const DEFAULT_CUTOFF = "12:00";
