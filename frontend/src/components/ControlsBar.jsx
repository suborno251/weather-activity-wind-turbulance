import { MAX_DATE, MIN_DATE } from "../config.js";

export default function ControlsBar({ date, cutoff, onChange, showDate = true }) {
  return (
    <section className="card controls">
      {showDate && (
        <div className="field">
          <label htmlFor="date">Delivery day (Jan 2026)</label>
          <input id="date" type="date" value={date} min={MIN_DATE} max={MAX_DATE} onChange={(e) => onChange({ date: e.target.value })} />
        </div>
      )}
      <div className="field">
        <label htmlFor="cutoff">Decision cutoff (day before)</label>
        <input id="cutoff" type="time" value={cutoff} onChange={(e) => onChange({ cutoff: e.target.value })} />
      </div>
      <p className="controls-note">Shows the latest forecast published before the cutoff for each half-hour of the delivery day.</p>
    </section>
  );
}
