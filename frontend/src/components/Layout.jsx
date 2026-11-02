import { NavLink, Outlet, useLocation } from "react-router-dom";

const links = [
  { to: "/", label: "Decision view", end: true },
  { to: "/accuracy", label: "Accuracy" },
  { to: "/method", label: "Method" },
];

export default function Layout() {
  const { search } = useLocation(); // keep filters when switching tabs
  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#5EEAD4" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
            <path d="M12 12V22M12 12L12 3M12 12L19 16M12 12L5 16" />
          </svg>
          <div>
            <div className="brand-title">Wind Forecast Monitor</div>
            <div className="brand-sub">GB national wind · Day-ahead purchasing</div>
          </div>
        </div>
        <nav className="nav">
          {links.map((l) => (
            <NavLink key={l.to} to={{ pathname: l.to, search }} end={l.end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <div className="footer-left">
          <span className="footer-title">Wind Forecast Monitor</span>
          <span className="footer-sep">·</span>
          <span>GB National Wind Power Purchasing</span>
        </div>
        <div className="footer-right">
          <a href="/docs" target="_blank" rel="noreferrer" className="footer-link">Swagger Docs</a>
          <span className="footer-sep">·</span>
          <span>Data source: <a href="https://bmrs.elexon.co.uk/" target="_blank" rel="noreferrer" className="footer-link">Elexon BMRS</a> (FUELHH &amp; WINDFOR)</span>
        </div>
      </footer>
    </div>
  );
}
