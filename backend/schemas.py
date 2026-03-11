"""
Pydantic v2 schemas for all ShopSerp API request / response models.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ─── Product ──────────────────────────────────────────────────────────────────


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    query: str = Field(..., min_length=1, max_length=1024)
    is_active: bool = True


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    query: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    monitors: list[MonitorResponse] = Field(default_factory=list)


# ─── Monitor ─────────────────────────────────────────────────────────────────


class MonitorCreate(BaseModel):
    product_id: int
    country_code: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    enabled: bool = True
    interval_minutes: int = Field(default=360, ge=5, le=44640)


class MonitorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    country_code: str
    enabled: bool
    interval_minutes: int
    last_checked: datetime | None = None
    created_at: datetime


# ─── PriceRecord ─────────────────────────────────────────────────────────────


class PriceRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    store_name: str
    store_domain: str
    price: float
    currency: str
    original_price: float | None = None
    url: str
    title: str
    condition: str | None = None
    shipping: str | None = None
    in_stock: bool
    is_reputable: bool
    scraped_at: datetime


# ─── PriceAlert ──────────────────────────────────────────────────────────────


class PriceAlertCreate(BaseModel):
    monitor_id: int
    alert_type: Literal["below_threshold", "price_drop", "back_in_stock"]
    threshold_value: float | None = None
    is_active: bool = True


class PriceAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    monitor_id: int
    alert_type: str
    threshold_value: float | None = None
    is_active: bool
    last_triggered: datetime | None = None
    created_at: datetime


# ─── Search ──────────────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1024)
    countries: list[str] = Field(default_factory=lambda: ["US"])
    max_results: int = Field(default=30, ge=1, le=100)


class SearchResultItem(BaseModel):
    store_name: str
    store_domain: str
    price: float
    currency: str
    original_price: float | None = None
    url: str
    title: str
    condition: str | None = None
    shipping: str | None = None
    in_stock: bool = True
    is_reputable: bool = False


class CountrySearchResults(BaseModel):
    country_code: str
    country_name: str
    currency: str
    results: list[SearchResultItem] = Field(default_factory=list)
    result_count: int = 0


class SearchResponse(BaseModel):
    query: str
    countries: list[CountrySearchResults] = Field(default_factory=list)
    total_results: int = 0


# ─── Analytics ───────────────────────────────────────────────────────────────


class StoreBreakdown(BaseModel):
    store_name: str
    store_domain: str
    avg_price: float
    min_price: float
    max_price: float
    record_count: int
    is_reputable: bool


class PriceDistributionBucket(BaseModel):
    range_low: float
    range_high: float
    count: int


class AnalyticsResponse(BaseModel):
    monitor_id: int
    avg_price: float
    min_price: float
    max_price: float
    median_price: float
    std_dev: float
    sample_count: int
    price_distribution: list[PriceDistributionBucket] = Field(default_factory=list)
    store_breakdown: list[StoreBreakdown] = Field(default_factory=list)


# ─── Price History ───────────────────────────────────────────────────────────


class PricePoint(BaseModel):
    timestamp: datetime
    price: float
    store_name: str
    currency: str


class PriceHistoryResponse(BaseModel):
    monitor_id: int
    data: list[PricePoint] = Field(default_factory=list)
    period_start: datetime | None = None
    period_end: datetime | None = None


# ─── Country Config ──────────────────────────────────────────────────────────


class CountryConfig(BaseModel):
    code: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    name: str
    currency: str = Field(..., description="ISO 4217 currency code")
    gl: str = Field(..., description="Google gl parameter value")
    hl: str = Field(..., description="Google hl parameter value")
    popular_stores: list[str] = Field(default_factory=list)


# ─── Generic ─────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    detail: str


# Forward-ref rebuild so ProductResponse can reference MonitorResponse.
ProductResponse.model_rebuild()
