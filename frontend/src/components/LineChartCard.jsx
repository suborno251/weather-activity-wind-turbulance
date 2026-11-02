import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function LineChartCard({ data, xKey, yKey, yName, label }) {
  return (
    <div className="chart" role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height={240}>
        <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="#E3EAE9" vertical={false} />
          <XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
          <YAxis width={56} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Line dataKey={yKey} name={yName} stroke="#C2410C" strokeWidth={3} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
