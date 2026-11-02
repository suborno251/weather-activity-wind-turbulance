import { Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// series: [{ time: "00:00", forecast, actual, lower, upper }]
export default function ForecastChart({ series }) {
  const data = series.map((p) => ({ ...p, band: p.lower != null && p.upper != null ? [p.lower, p.upper] : null }));
  return (
    <div className="chart" role="img" aria-label="Forecast versus actual wind generation over the delivery day">
      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#E3EAE9" vertical={false} />
          <XAxis dataKey="time" interval={5} tick={{ fontSize: 12 }} />
          <YAxis unit=" MW" width={80} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Area dataKey="band" name="P5–P95 error band" stroke="none" fill="#CCE9E5" />
          <Line dataKey="forecast" name="Forecast (latest before cutoff)" stroke="#0F766E" strokeWidth={3} dot={false} />
          <Line dataKey="actual" name="Actual" stroke="#C2410C" strokeWidth={3} dot={false} connectNulls={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
