# Wind Forecast Monitor — Backend API

> FastAPI service providing day-ahead wind generation forecasts and quantitative accuracy metrics for UK power procurement decisions. Built for the **REint Full Stack SWE Challenge**.

---

## 1. Overview & Business Context

UK energy utilities buy electricity from the day-ahead wholesale market to serve consumer demand. Decisions for delivery day $D$ are finalized on $D-1$ before a gate-closure cutoff. Because wind power is weather-dependent, buyers must understand:
1. **Latest Available Wind Generation Forecasts**: The exact forecast published prior to the day-ahead cutoff.
2. **Quantified Error & Downside Risk**: Historical error margins (P95) to decide how much additional thermal/gas power must be secured to avoid costly imbalance charges.

This backend ingests national GB wind actuals (`FUELHH`) and forecasts (`WINDFOR`) from the Elexon BMRS API for January 2026 and exposes REST endpoints for analysis.

---

## 2. API Endpoints

### `GET /api/health`
Health check endpoint.
- **Response**: `{"status": "ok"}`

### `GET /api/decision`
Returns the operational decision snapshot for a given delivery date and day-ahead cutoff.
- **Query Parameters**:
  - `date` (required): Delivery date in January 2026 (e.g. `2026-01-15`).
  - `cutoff` (optional, default `12:00`): Cutoff time (HH:MM) on day $D-1$.
- **Response**:
  ```json
  {
    "kpis": { "peak_mw": 15813.0, "peak_time": "00:00", "avg_mw": 11757.5 },
    "series": [
      { "time": "00:00", "forecast": 15813, "actual": 14602, "lower": 11126.9, "upper": 16586.0 }
    ],
    "periods": [
      { "label": "Night 00:00–06:00", "forecast_mw": 14990.7, "p95_error_mw": 5928.5, "low_wind_mw": 9062.2 }
    ]
  }
  ```

### `GET /api/accuracy`
Returns aggregated forecast accuracy metrics across January 2026 for a specified cutoff.
- **Query Parameters**:
  - `cutoff` (optional, default `12:00`): Cutoff time (HH:MM) on day $D-1$.
- **Response**:
  ```json
  {
    "metrics": { "mae": 2002.9, "rmse": 2470.1, "bias": 1805.9, "median_abs": 1709.5, "p95": 4686.1 },
    "daily": [{ "date": "01 Jan", "mae": 4249.3 }],
    "histogram": [{ "bin": "-500", "count": 12 }],
    "by_slot": [{ "slot": "00:00", "mae": 1950.2 }],
    "by_horizon": [{ "horizon_h": 24, "mae": 2100.5 }],
    "cutoff_comparison": [
      { "cutoff": "06:00", "mae": 2210.0, "rmse": 2700.0, "bias": 1950.0, "p95": 5100.0 },
      { "cutoff": "12:00", "mae": 2002.9, "rmse": 2470.1, "bias": 1805.9, "p95": 4686.1 }
    ]
  }
  ```

---

## 3. Repository & Directory Structure

```text
.
├── app.py               # FastAPI entrypoint, middleware, Swagger routing, and router registration
├── config.py            # Global settings, Elexon endpoints, scope dates, and delivery periods
├── schemas.py           # Pydantic request & response models with OpenAPI documentation
├── routers/
│   ├── health.py        # /api/health operational monitoring route
│   ├── decision.py      # /api/decision day-ahead snapshot & procurement buffer route
│   └── accuracy.py      # /api/accuracy statistical metrics & cutoff benchmarking route
├── services/
│   ├── elexon.py        # Elexon BMRS API client (FUELHH actuals & WINDFOR forecasts)
│   └── analysis.py      # Cutoff matching algorithm, KPI metrics, and horizon decay
├── requirements.txt     # Python dependencies (FastAPI, pandas, numpy, uvicorn, requests, httpx)
├── Dockerfile           # Production Python 3.12-slim Docker container
├── .gitignore           # Python virtualenv and cache exclusions
├── README.md            # Backend documentation & API specification
└── data/
    ├── actuals.csv      # Elexon BMRS FUELHH wind generation actuals (Jan 2026)
    └── forecasts.csv    # Elexon BMRS WINDFOR forecasts with publish timestamps
```

---

## 4. How to Run

### Using Docker
```bash
# Build the container
docker build -t wind-backend .

# Run the container on port 8000
docker run -p 8000:8000 -v $(pwd)/data:/app/data wind-backend
```
- API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Local Development (Virtualenv)
```bash
# 1. Create and activate a virtual environment
python -m venv env
source env/bin/activate    # On Windows: env\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the ASGI server
uvicorn app:app --reload --port 8000
```

---

## 5. Refreshing Data from Elexon BMRS (Optional)

The `data/` directory includes pre-downloaded January 2026 data. To re-fetch fresh data directly from Elexon's live streaming API:

```bash
python app.py refresh
```

---

## 6. Related Repositories & Deployment

- **Frontend Repository**: `[Add link to your Frontend repo here]`
- **Live Deployment**: `[Add link to your deployed backend/frontend here]`
- **Video Walkthrough**: `[Add your YouTube video link here]`

---

## 7. AI Tools Disclosure

In accordance with challenge guidelines, **Google Antigravity (Gemini CLI)** was used during development to assist with code structure review, NumPy scalar serialization handling in FastAPI, and documentation formatting.
