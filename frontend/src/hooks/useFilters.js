import { useSearchParams } from "react-router-dom";
import { DEFAULT_CUTOFF, DEFAULT_DATE } from "../config.js";

// Filters live in the URL so a view can be shared or bookmarked.
export function useFilters() {
  const [params, setParams] = useSearchParams();
  const date = params.get("date") || DEFAULT_DATE;
  const cutoff = params.get("cutoff") || DEFAULT_CUTOFF;
  const update = (next) => setParams({ date, cutoff, ...next });
  return { date, cutoff, update };
}
