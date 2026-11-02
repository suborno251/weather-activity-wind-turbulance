import { fmtMw, fmtSigned } from "../api.js";
import BarChartCard from "../components/BarChartCard.jsx";
import Card from "../components/Card.jsx";
import ControlsBar from "../components/ControlsBar.jsx";
import DataTable from "../components/DataTable.jsx";
import ForecastChart from "../components/ForecastChart.jsx";
import KpiCard from "../components/KpiCard.jsx";
import State from "../components/State.jsx";
import { useApi } from "../hooks/useApi.js";
import { useFilters } from "../hooks/useFilters.js";

export default function Decision() {
  const { date, cutoff, update } = useFilters();
  const dec = useApi("/api/decision", { date, cutoff });
  const acc = useApi("/api/accuracy", { cutoff });

  return (
    <>
      <ControlsBar date={date} cutoff={cutoff} onChange={update} />

      <State loading={dec.loading || acc.loading} error={dec.error || acc.error}>
        {dec.data && acc.data && (
          <>
            <section className="kpis">
              <KpiCard label="Forecast peak" value={fmtMw(dec.data.kpis.peak_mw)} note={`at ${dec.data.kpis.peak_time}`} />
              <KpiCard label="Forecast daily average" value={fmtMw(dec.data.kpis.avg_mw)} />
              <KpiCard label="MAE (January)" value={fmtMw(acc.data.metrics.mae)} note="mean absolute error" />
              <KpiCard label="Bias" value={fmtSigned(acc.data.metrics.bias)} note="positive = over-forecast" />
              <KpiCard label="P95 absolute error" value={fmtMw(acc.data.metrics.p95)} note="buffer to plan for" />
            </section>

            <Card title="Forecast vs actual wind generation">
              <ForecastChart series={dec.data.series} />
            </Card>

            <section className="grid-2">
              <Card title="Daily error across January (MAE)">
                <BarChartCard data={acc.data.daily} xKey="date" yKey="mae" yName="MAE (MW)" label="Daily mean absolute error" />
              </Card>
              <Card title="Error distribution">
                <BarChartCard data={acc.data.histogram} xKey="bin" yKey="count" yName="Half-hours" color="#C2410C" label="Histogram of forecast errors" />
              </Card>
            </section>

            <Card title="Planning summary: extra power to procure">
              <DataTable
                columns={[
                  { key: "label", label: "Period" },
                  { key: "forecast_mw", label: "Forecast wind", render: (v) => fmtMw(v) },
                  { key: "p95_error_mw", label: "Typical error (P95)", render: (v) => `± ${fmtMw(v)}` },
                  { key: "low_wind_mw", label: "Low-wind case", render: (v) => fmtMw(v) },
                ]}
                rows={dec.data.periods}
              />
            </Card>
          </>
        )}
      </State>
    </>
  );
}
