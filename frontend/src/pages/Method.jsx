import Card from "../components/Card.jsx";

const steps = [
  ["Pick the cutoff", "For a delivery day, fix the decision time on the day before."],
  ["Take the latest forecast", "For each half-hour, use the forecast with the latest publish time that is still before the cutoff."],
  ["Compare with actuals", "Match each slot to the actual wind generation and compute the error."],
];

export default function Method() {
  return (
    <>
      <Card title="How this works">
        <p className="prose">The numbers shown are what a buyer would have seen at the day-ahead decision point, compared with what wind actually delivered.</p>
      </Card>

      <section className="grid-3">
        {steps.map(([title, text], i) => (
          <Card key={title} title={`${i + 1}. ${title}`}>
            <p className="prose">{text}</p>
          </Card>
        ))}
      </section>

      <section className="grid-2">
        <Card title="Metric definitions">
          <dl className="defs">
            <dt>MAE</dt><dd>Average size of the error, ignoring direction.</dd>
            <dt>RMSE</dt><dd>Like MAE but penalises large misses more.</dd>
            <dt>Bias</dt><dd>Average signed error. Positive means the forecast runs high.</dd>
            <dt>P95 absolute error</dt><dd>The error size exceeded only 5% of the time. Use it as a planning buffer.</dd>
          </dl>
        </Card>
        <Card title="Data sources and limitations">
          <ul className="list">
            <li>Actuals: Elexon BMRS FUELHH, wind fuel type, 30-minute resolution.</li>
            <li>Forecasts: Elexon BMRS WINDFOR, with start time and publish time.</li>
            <li>Scope: national GB wind, January 2026 decisions.</li>
            <li>Wind only, no solar or demand data.</li>
            <li>Missing actuals or forecasts are excluded from the metrics.</li>
          </ul>
        </Card>
      </section>
    </>
  );
}
