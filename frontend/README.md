# Wind Forecast Monitor — Frontend Application

> Modern React 18 dashboard for UK energy utility day-ahead wind generation monitoring and power procurement decision support. Built for the **REint Full Stack SWE Challenge**.

---

## 1. Overview & Business Context

UK energy utilities purchase electricity from the wholesale day-ahead market to serve consumers. Because wind power is weather-dependent, power purchase decisions made on $D-1$ rely on forecasts available at the decision gate closure (cutoff).

This dashboard enables utility buyers to:
1. **Understand Latest Renewable Forecasts**: Inspect the exact wind forecast published before the chosen cutoff for any delivery day in January 2026.
2. **Quantify Forecast Error & Procurement Risk**: Leverage historical error distributions (P95 error margins) to decide how much additional thermal/gas power must be secured without incurring imbalance penalties.

---

## 2. Key Pages & Features

- **Decision View (`/`)**:
  - **Forecast vs Actual Profile**: Intraday generation curves with historical P5–P95 error bands.
  - **Planning Summary Table**: Breaks the delivery day into 4 periods (Night, Morning, Afternoon, Evening) with average forecast generation, P95 error margins, and the conservative low-wind case to guide thermal procurement.
  - **Visual Distribution**: Error histogram and daily Mean Absolute Error (MAE) chart.
- **Accuracy View (`/accuracy`)**:
  - **Executive KPIs**: MAE, Root Mean Square Error (RMSE), Bias, Median Absolute Error, and P95 planning buffer.
  - **Diurnal Patterns**: Error breakdown by 30-minute settlement slot.
  - **Forecast Horizon Decay**: Accuracy degradation across 0 to 48 hours publish horizon.
  - **Cutoff Comparison Table**: Benchmark performance across `06:00`, `09:00`, `12:00`, and `15:00` cutoffs.
- **Method View (`/method`)**:
  - Transparent documentation of the cutoff matching algorithm, metric definitions, and Elexon dataset scope.
- **URL-Persisted State**:
  - Date and cutoff selections persist in URL query parameters (`?date=2026-01-15&cutoff=12:00`) for seamless sharing and state retention across tabs.

---

## 3. Repository & Directory Structure

```text
.
├── package.json         # React 18, React Router 6, Recharts, Vite dependencies
├── vite.config.js       # Vite build config with local dev proxy (/api -> localhost:8000)
├── index.html           # HTML5 entry template
├── nginx.conf           # Production Nginx reverse proxy configuration
├── Dockerfile           # Multi-stage Docker build (Node.js build -> Nginx runtime)
├── vercel.json          # SPA rewrite rules for Vercel deployment
├── .gitignore           # Node modules and build output exclusions
├── README.md            # Frontend documentation & setup guide
└── src/
    ├── main.jsx         # React DOM entry
    ├── App.jsx          # Route configuration
    ├── styles.css       # Design tokens, responsive grid, and layout styling
    ├── api.js           # API request helpers and number formatters
    ├── config.js        # Challenge scope dates and default parameters
    ├── hooks/
    │   ├── useApi.js    # Data fetching hook with loading, error, and cancellation states
    │   └── useFilters.js# URL search param synchronization for date/cutoff
    ├── components/
    │   ├── Layout.jsx   # App frame with header navigation and Elexon attribution footer
    │   ├── Card.jsx     # Card container
    │   ├── ControlsBar.jsx # Date and cutoff input controls
    │   ├── DataTable.jsx# Accessible table component
    │   ├── ForecastChart.jsx # Composed line & area chart with confidence bands
    │   ├── BarChartCard.jsx  # Reusable bar chart
    │   ├── LineChartCard.jsx # Reusable line chart
    │   ├── KpiCard.jsx  # Metric indicator card
    │   └── State.jsx    # Loading spinner and error boundary banners
    └── pages/
        ├── Decision.jsx # Day-ahead purchasing decision view
        ├── Accuracy.jsx # Forecast accuracy evaluation page
        └── Method.jsx   # Methodology documentation
```

---

## 4. How to Run

### Local Development
```bash
# 1. Install dependencies
npm install

# 2. Start the dev server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173). In development, API requests to `/api/*` are automatically proxied to `http://localhost:8000`.

### Production Build
```bash
npm run build
npm run preview
```

### Docker
```bash
# Build the Docker image
docker build -t wind-frontend .

# Run the container on port 8080
docker run -p 8080:80 wind-frontend
```
Open [http://localhost:8080](http://localhost:8080).

---

## 5. Deployment (Vercel)

1. Connect this repository to **Vercel**.
2. Set the Root Directory to `./` (or leave default).
3. Set the Environment Variable:
   - `VITE_API_URL` = `<Your deployed backend URL>` (e.g. `https://your-backend.onrender.com`).
4. Deploy.

---

## 6. Related Repositories & Deliverables

- **Backend Repository**: `[Add link to your Backend repo here]`
- **Live Application**: `[Add your Vercel deployment link here]`
- **Video Walkthrough**: `[Add your YouTube video link here]`

---

## 7. AI Tools Disclosure

In accordance with the challenge guidelines, **Google Antigravity (Gemini CLI)** was used during development for component verification, styling adjustments (sticky footer and responsive layout), and documentation formatting.
