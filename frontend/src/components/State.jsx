// Shows loading / error messages; renders children once data is ready.
export default function State({ loading, error, children }) {
  if (loading) return <p className="state">Loading…</p>;
  if (error) return <p className="state error" role="alert">Could not load data: {error.message}. Check that the backend is running and try again.</p>;
  return children;
}
