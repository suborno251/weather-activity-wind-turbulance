export default function Card({ title, subtitle, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {title && <h2 className="card-title">{title}</h2>}
      {subtitle && <p className="card-sub">{subtitle}</p>}
      {children}
    </section>
  );
}
