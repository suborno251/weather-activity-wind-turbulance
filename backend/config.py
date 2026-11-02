"""Configuration settings and constants for Wind Forecast Monitor."""
from __future__ import annotations

import os
from datetime import date as Date, datetime
from pathlib import Path

BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")
DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent / "data"))
ACTUALS_CSV = DATA_DIR / "actuals.csv"
FORECASTS_CSV = DATA_DIR / "forecasts.csv"

LONDON = "Europe/London"
SCOPE_START = Date(2026, 1, 1)   # delivery days in scope
SCOPE_END = Date(2026, 1, 31)

# Forecasts for 1 Jan can be published on 31 Dec, so fetch a little earlier.
FETCH_PUBLISH_FROM = datetime(2025, 12, 28)
FETCH_CHUNK_DAYS = int(os.getenv("FETCH_CHUNK_DAYS", "3"))

COMPARE_CUTOFFS = ["06:00", "09:00", "12:00", "15:00"]
PERIODS = [
    ("Night 00:00–06:00", 0, 6),
    ("Morning 06:00–12:00", 6, 12),
    ("Afternoon 12:00–18:00", 12, 18),
    ("Evening 18:00–24:00", 18, 24),
]

TAGS_METADATA = [
    {
        "name": "Decision Support",
        "description": "Day-ahead forecast evaluation with gate-closure cutoff filtering and procurement risk buffers.",
    },
    {
        "name": "Forecast Accuracy",
        "description": "Historical error analysis including MAE, RMSE, diurnal bias, horizon decay, and cutoff benchmarking.",
    },
    {
        "name": "System",
        "description": "Operational health check and diagnostics.",
    },
]
