import { fmtMw, fmtSigned } from "../api.js";
import BarChartCard from "../components/BarChartCard.jsx";
import Card from "../components/Card.jsx";
import ControlsBar from "../components/ControlsBar.jsx";
import DataTable from "../components/DataTable.jsx";
import KpiCard from "../components/KpiCard.jsx";
import LineChartCard from "../components/LineChartCard.jsx";
import State from "../components/State.jsx";
import { useApi } from "../hooks/useApi.js";
import { useFilters } from "../hooks/useFilters.js";

export default function Accuracy() {
  const { date, cutoff, update } = useFilters();
  const { data, error, loading } = useApi("/api/accuracy", { cutoff });

  return (
    <>
      <ControlsBar date={date} cutoff={cutoff} onChange={update} showDate={false} />
      <State loading={loading} error={error}>
        {data && (
          <>
            <section className="kpis">
              <KpiCard label="MAE" value={fmtMw(data.metrics.mae)} />
              <KpiCard label="RMSE" value={fmtMw(data.metrics.rmse)} />
              <KpiCard label="Bias" value={fmtSigned(data.metrics.bias)} />
              <KpiCard label="Median absolute error" value={fmtMw(data.metrics.median_abs)} />
              <KpiCard label="P95 absolute error" value={fmtMw(data.metrics.p95)} />
            </section>

            <section className="grid-2">
              <Card title="Error by time of day" subtitle="Mean absolute error per half-hour slot">
                <BarChartCard data={data.by_slot} xKey="slot" yKey="mae" yName="MAE (MW)" xInterval={5} label="Error by half-hour slot" />
              </Card>
              <Card title="Error vs forecast horizon" subtitle="Hours between publish time and target time">
                <LineChartCard data={data.by_horizon} xKey="horizon_h" yKey="mae" yName="MAE (MW)" label="Error against forecast horizon" />
              </Card>
            </section>

            <Card title="Compare decision cutoffs">
              <DataTable
                columns={[
                  { key: "cutoff", label: "Cutoff" },
                  { key: "mae", label: "MAE", render: (v) => fmtMw(v) },
                  { key: "rmse", label: "RMSE", render: (v) => fmtMw(v) },
                  { key: "bias", label: "Bias", render: (v) => fmtSigned(v) },
                  { key: "p95", label: "P95", render: (v) => fmtMw(v) },
                ]}
                rows={data.cutoff_comparison}
              />
            </Card>
          </>
        )}
      </State>
    </>
  );
}
