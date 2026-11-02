import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

// Generic bar chart used for daily MAE, error by slot and the error histogram.
export default function BarChartCard({ data, xKey, yKey, yName, color = "#0F766E", label, xInterval = "preserveEnd" }) {
  return (
    <div className="chart" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#E3EAE9" vertical={false} />
          <XAxis dataKey={xKey} interval={xInterval} tick={{ fontSize: 12 }} />
          <YAxis width={56} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey={yKey} name={yName} fill={color} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
