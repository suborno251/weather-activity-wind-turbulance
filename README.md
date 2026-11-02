# Wind Forecast Monitor

> Day-ahead renewable generation forecasting and procurement decision portal for UK power utilities. Built for the **REint Full Stack SWE Challenge**.

---

## 1. Problem Overview & Business Context

UK energy utilities purchase power from the UK wholesale day-ahead market to satisfy consumer electricity demand. Power purchase decisions for delivery day $D$ must be finalized one day prior ($D-1$) by a specific gate closure / cutoff time. 

Because renewable wind generation is weather-dependent and intermittent, procurement teams need to understand:
1. **Latest Available Generation Forecasts**: Exactly what wind forecast was available at the specific day-ahead decision cutoff.
2. **Quantified Forecast Accuracy & Downside Risk**: How much error is historically expected, allowing buyers to determine the exact volume of additional power (e.g. from thermal or gas peaking plants) to procure without facing costly imbalance charges.

This application ingests national GB wind actuals (`FUELHH`) and forecasts (`WINDFOR`) from Elexon BMRS for **January 2026** and delivers an interactive decision-support tool.

---

## 2. Key Features

- **Decision View**:
  - **Dynamic Cutoff Filtering**: Select any delivery date in January 2026 and cutoff time on $D-1$ (e.g. `12:00`). The system filters only forecasts published *prior* to that cutoff.
  - **Intraday Profile & Confidence Bands**: Forecast vs actual generation with historical P5–P95 error bands.
  - **Procurement Planning Table**: Breaks down the delivery day into 4 key periods (Night, Morning, Afternoon, Evening) with average expected wind, P95 typical error, and low-wind procurement requirements.
  - **Error Distribution & Daily Trends**: Interactive error histogram and daily MAE bar chart.
- **Accuracy View**:
  - **Quantitative KPI Cards**: Mean Absolute Error (MAE), Root Mean Square Error (RMSE), Bias (systematic over/under-forecast), Median Absolute Error, and P95 planning buffer.
  - **Error by Half-Hour Settlement Slot**: Pinpoints diurnal error patterns (e.g., peak demand slots).
  - **Forecast Horizon Decay**: Demonstrates how forecast accuracy degrades as the publish horizon increases from 0 to 48 hours.
  - **Cutoff Comparison Matrix**: Compares forecast performance across standard industry cutoffs (`06:00`, `09:00`, `12:00`, `15:00`).
- **Method View**:
  - Full transparency on cutoff filtering logic, mathematical metric definitions, and Elexon dataset limitations.
- **Filter Persistence**:
  - URL-synchronized search parameters (`?date=2026-01-15&cutoff=12:00`) for shareable, bookmarkable analysis views.

---

## 3. Repository & File Structure

```text
.
├── Dockerfile                   # Root Dockerfile for cloud platforms (Render, Railway)
├── docker-compose.yml           # Multi-container orchestration (FastAPI + Nginx)
├── README.md                    # Root project documentation & challenge deliverables
├── .gitignore                   # Root git exclusion rules
├── backend/
│   ├── app.py                   # FastAPI entrypoint, middleware, and router registration
│   ├── config.py                # Global settings, Elexon endpoints, scope dates, and delivery periods
│   ├── schemas.py               # Pydantic request & response models with OpenAPI documentation
│   ├── routers/
│   │   ├── health.py            # /api/health operational monitoring route
│   │   ├── decision.py          # /api/decision day-ahead snapshot & procurement buffer route
│   │   └── accuracy.py          # /api/accuracy statistical metrics & cutoff benchmarking route
│   ├── services/
│   │   ├── elexon.py            # Elexon BMRS API client (FUELHH actuals & WINDFOR forecasts)
│   │   └── analysis.py          # Cutoff matching algorithm, KPI metrics, and horizon decay
│   ├── requirements.txt         # Python dependencies (FastAPI, pandas, numpy, uvicorn, requests)
│   ├── Dockerfile               # Production Python 3.12 container specification
│   ├── .gitignore               # Backend-specific exclusions
│   └── data/
│       ├── actuals.csv          # Cached Elexon FUELHH wind generation actuals (Jan 2026)
│       └── forecasts.csv        # Cached Elexon WINDFOR forecasts with publish timestamps
└── frontend/
    ├── package.json             # Frontend dependencies (React 18, React Router 6, Recharts, Vite)
    ├── vite.config.js           # Vite dev server configuration with /api proxy
    ├── index.html               # Single-page application entry HTML
    ├── nginx.conf               # Production Nginx reverse proxy configuration
    ├── Dockerfile               # Multi-stage Docker build (Node.js build -> Nginx runtime)
    ├── vercel.json              # Vercel SPA rewrite rules
    ├── README.md                # Frontend-specific documentation
    └── src/
        ├── main.jsx             # React DOM root entry
        ├── App.jsx              # Client-side router configuration
        ├── styles.css           # Clean, accessible styling & CSS variables
        ├── api.js               # API fetch utilities and number formatters
        ├── config.js            # Challenge constants (Jan 2026 dates, default cutoffs)
        ├── hooks/
            ├── useApi.js        # Data fetching hook with AbortController and loading/error states
            └── useFilters.js    # Synchronizes date/cutoff filter state with URL search params
        ├── components/
            ├── Layout.jsx       # App shell: header navigation, outlet, and responsive footer
            ├── Card.jsx         # Clean card container for metrics and charts
            ├── ControlsBar.jsx  # Date and cutoff time input selectors
            ├── KpiCard.jsx      # Stat display card with labels and secondary notes
            ├── DataTable.jsx    # Accessible, responsive data table
            ├── ForecastChart.jsx# Composed area & line chart for forecast vs actual + error bands
            ├── BarChartCard.jsx # Reusable bar chart (daily error, slot error, histogram)
            ├── LineChartCard.jsx# Horizon error line chart
            └── State.jsx        # Loading indicators and error boundary banner
        └── pages/
            ├── Decision.jsx     # Main day-ahead purchasing decision view
            ├── Accuracy.jsx     # Comprehensive forecast evaluation and benchmark page
            └── Method.jsx       # Methodology documentation and definitions
```

---

## 4. How to Start the Application

### Option 1: Docker Compose (Recommended)

Run both the frontend and backend with a single command:

```bash
docker compose up --build
```

- **Web Application (UI)**: [http://localhost:8080](http://localhost:8080)
- **Backend API (Swagger Docs)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Backend Health Check**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

*(Nginx listens on port `8080`, serves the React build, and reverse-proxies `/api` requests to the FastAPI backend).*

---

### Option 2: Local Development (Without Docker)

#### Prerequisites
- Python 3.11+
- Node.js 18+ & npm

#### 1. Start the Backend:
```bash
cd backend
python -m venv env
source env/bin/activate        # On Windows: env\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

#### 2. Start the Frontend:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173). Requests to `/api` are automatically proxied to `http://localhost:8000`.

---

### Refreshing Elexon Data (Optional)

The repository includes pre-downloaded January 2026 Elexon datasets in `backend/data/`. If you want to re-stream the data directly from the official Elexon BMRS API:

```bash
cd backend
python app.py refresh
```

---

## 5. Deployment Guide (Single Repository)

### A. Deploy Backend (Render, Railway, or Heroku)
1. Create a new **Web Service** pointing to this repository.
2. Set the **Root Directory** to `backend`.
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
5. Note your public backend URL (e.g. `https://wind-backend.onrender.com`).

### B. Deploy Frontend (Vercel)
1. Import this repository into **Vercel**.
2. In the project settings, set **Root Directory** to `frontend`.
3. Under **Environment Variables**, add:
   - `VITE_API_URL` = `https://wind-backend.onrender.com` (your deployed backend URL)
4. Click **Deploy**.

### C. Keep-Alive Cron (Prevents Render Free Tier Cold Starts)
Render free services spin down after 15 minutes of inactivity. To keep your service perpetually warm and responsive:
1. **GitHub Actions Cron Workflow** (`.github/workflows/keep-alive.yml`): Automatically pings `GET /api/health` every 14 minutes.
2. In your GitHub repository under **Settings** > **Secrets and variables** > **Actions**, optionally set:
   - Variable `BACKEND_URL`: `https://weather-activity-wind-turbulance.onrender.com` (or your chosen Render URL).
3. The backend also includes a built-in background keep-alive task in `app.py` that pings Render's `RENDER_EXTERNAL_URL` every 12 minutes while running.

---

## 6. Live Deployment & Video Deliverables

- **Live Application**: `[Add your Vercel deployment URL here]`
- **Video Walkthrough (Unlisted YouTube)**: `[Add your YouTube video link here]`

---

## 7. AI Tools Disclosure

In accordance with the challenge guidelines, **Google Antigravity (Gemini CLI)** was used during this project to assist with code structure verification, debugging FastAPI NumPy scalar serialization, and refining documentation. All data modeling, requirements analysis, and system architecture decisions were evaluated and verified against the challenge specification.
