"""Pydantic schemas and response models for Wind Forecast Monitor API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Service health status", json_schema_extra={"example": "ok"})


class SeriesPoint(BaseModel):
    time: str = Field(description="Half-hour slot time (HH:MM) in GB local time", json_schema_extra={"example": "12:00"})
    forecast: float | None = Field(description="Wind generation forecast in MW", json_schema_extra={"example": 8500.5})
    actual: float | None = Field(description="Actual wind generation delivered in MW", json_schema_extra={"example": 8210.0})
    lower: float = Field(description="P5 conservative lower bound (forecast - Q95 error)", json_schema_extra={"example": 6800.0})
    upper: float = Field(description="P95 upper bound (forecast - Q05 error)", json_schema_extra={"example": 9600.0})


class ProcurementPeriod(BaseModel):
    label: str = Field(description="Delivery block label", json_schema_extra={"example": "Morning 06:00–12:00"})
    forecast_mw: float = Field(description="Mean expected wind generation in MW", json_schema_extra={"example": 7400.2})
    p95_error_mw: float = Field(description="Historical P95 error buffer in MW", json_schema_extra={"example": 1850.0})
    low_wind_mw: float = Field(description="Conservative baseline generation (Forecast - P95 buffer)", json_schema_extra={"example": 5550.2})


class DecisionKpis(BaseModel):
    peak_mw: float = Field(description="Peak expected wind generation across delivery day in MW", json_schema_extra={"example": 11200.0})
    peak_time: str = Field(description="Time of peak wind generation", json_schema_extra={"example": "14:30"})
    avg_mw: float = Field(description="Daily average expected wind generation in MW", json_schema_extra={"example": 8100.5})


class DecisionResponse(BaseModel):
    kpis: DecisionKpis = Field(description="High-level day summary KPIs")
    series: list[SeriesPoint] = Field(description="48 half-hour settlement slot forecast vs actual series with uncertainty bands")
    periods: list[ProcurementPeriod] = Field(description="4-block operational procurement planning breakdown")


class Metrics(BaseModel):
    mae: float | None = Field(description="Mean Absolute Error in MW", json_schema_extra={"example": 1450.5})
    rmse: float | None = Field(description="Root Mean Square Error in MW", json_schema_extra={"example": 1890.2})
    bias: float | None = Field(description="Mean error in MW (forecast - actual, positive = over-forecast)", json_schema_extra={"example": 120.3})
    median_abs: float | None = Field(description="Median absolute error in MW", json_schema_extra={"example": 1150.0})
    p95: float | None = Field(description="95th percentile absolute error buffer in MW", json_schema_extra={"example": 3200.0})


class DailyAccuracy(BaseModel):
    date: str = Field(description="Delivery date (DD Mon)", json_schema_extra={"example": "15 Jan"})
    mae: float = Field(description="Mean Absolute Error for this day in MW", json_schema_extra={"example": 1620.4})


class HistogramBin(BaseModel):
    bin: str = Field(description="Error bin start in MW", json_schema_extra={"example": "-1000"})
    count: int = Field(description="Frequency count of half-hour slots in this bin", json_schema_extra={"example": 42})


class SlotAccuracy(BaseModel):
    slot: str = Field(description="Half-hour slot time (HH:MM)", json_schema_extra={"example": "17:30"})
    mae: float = Field(description="Mean Absolute Error across month for this slot in MW", json_schema_extra={"example": 1820.0})


class HorizonDecay(BaseModel):
    horizon_h: int = Field(description="Forecast horizon hours ahead of delivery", json_schema_extra={"example": 24})
    mae: float = Field(description="Mean Absolute Error in MW", json_schema_extra={"example": 1950.0})


class CutoffComparisonItem(BaseModel):
    cutoff: str = Field(description="Gate closure cutoff time", json_schema_extra={"example": "12:00"})
    mae: float | None = Field(description="Mean Absolute Error in MW", json_schema_extra={"example": 1450.5})
    rmse: float | None = Field(description="Root Mean Square Error in MW", json_schema_extra={"example": 1890.2})
    bias: float | None = Field(description="Signed bias in MW", json_schema_extra={"example": 120.3})
    p95: float | None = Field(description="P95 error buffer in MW", json_schema_extra={"example": 3200.0})


class AccuracyResponse(BaseModel):
    metrics: Metrics = Field(description="Overall aggregate error KPIs for selected cutoff")
    daily: list[DailyAccuracy] = Field(description="Daily MAE timeline across January 2026")
    histogram: list[HistogramBin] = Field(description="Error distribution histogram bins")
    by_slot: list[SlotAccuracy] = Field(description="Diurnal error profile by settlement half-hour")
    by_horizon: list[HorizonDecay] = Field(description="Error decay by forecast publication horizon (0–48h)")
    cutoff_comparison: list[CutoffComparisonItem] = Field(description="Accuracy comparison across standard industry cutoffs")
