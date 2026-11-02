"""Wind Forecast Monitor: FastAPI backend entrypoint.

Serves GB national wind forecast vs actual analysis for January 2026 day-ahead decisions.

Run:      uvicorn app:app --reload --port 8000
Refresh:  python app.py refresh      (downloads Elexon data into ./data as CSV)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure backend root is in sys.path for direct module imports
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np
from fastapi import FastAPI
from fastapi.encoders import encoders_by_class_tuples
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import RedirectResponse

from config import ACTUALS_CSV, FORECASTS_CSV, TAGS_METADATA
from routers import accuracy, decision, health
# Re-exports for backwards compatibility
from services.analysis import latest_before_cutoff, load_store  # noqa: F401
from services.elexon import refresh_data  # noqa: F401

# Ensure NumPy scalar types serialize properly in FastAPI responses
encoders_by_class_tuples[int] = (np.integer,)
encoders_by_class_tuples[float] = (np.floating,)

app = FastAPI(
    title="Wind Forecast Monitor API",
    description="""
## Day-Ahead Wind Forecast & Procurement Portal API

Interactive Swagger API for GB national renewable wind generation analysis based on Elexon BMRS data (**January 2026**).

### Features:
- **Decision View**: Reproduces exact forecasts known prior to cutoff on $D-1$ and calculates procurement buffers.
- **Accuracy View**: Measures historical forecast accuracy (MAE, RMSE, Bias, P95) and cutoff comparisons.
- **Interactive Documentation**: Test endpoints live with Swagger UI below or via `/docs` and `/redoc`.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=TAGS_METADATA,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------------- Swagger/Docs aliases
@app.get("/swagger", include_in_schema=False)
def swagger_ui_redirect():
    """Redirect /swagger to /docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/docs", include_in_schema=False)
def api_docs_ui():
    """Serve Swagger UI directly under /api/docs for reverse proxies that only expose /api."""
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="Wind Forecast Monitor API - Swagger UI")


@app.get("/api/openapi.json", include_in_schema=False)
def api_openapi_schema():
    """Serve OpenAPI JSON schema under /api for reverse proxies."""
    return app.openapi()


# ----------------------------------------------------------------------------- Mount Routers
app.include_router(health.router)
app.include_router(decision.router)
app.include_router(accuracy.router)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        refresh_data()
        print(f"Saved {ACTUALS_CSV} and {FORECASTS_CSV}")
    else:
        print("Usage: python app.py refresh   |   uvicorn app:app --port 8000")
