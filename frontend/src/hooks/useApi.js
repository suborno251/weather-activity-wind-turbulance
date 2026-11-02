import { useEffect, useState } from "react";
import { getJson } from "../api.js";

export function useApi(path, params) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const key = JSON.stringify(params);

  useEffect(() => {
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: null }));
    getJson(path, params, ctrl.signal)
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => {
        if (error.name !== "AbortError") setState({ data: null, error, loading: false });
      });
    return () => ctrl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key]);

  return state;
}
