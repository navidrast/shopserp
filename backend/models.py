"""
SQLAlchemy ORM models for ShopSerp.

All models inherit from the shared declarative Base defined in database.py.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    query: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=_utcnow,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    monitors: Mapped[list["Monitor"]] = relationship(
        "Monitor", back_populates="product", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Product id={self.id} name={self.name!r}>"


class Monitor(Base):
    __tablename__ = "monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=360, nullable=False)
    last_checked: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="monitors")
    price_records: Mapped[list["PriceRecord"]] = relationship(
        "PriceRecord", back_populates="monitor", cascade="all, delete-orphan", lazy="selectin"
    )
    alerts: Mapped[list["PriceAlert"]] = relationship(
        "PriceAlert", back_populates="monitor", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_monitors_product_country", "product_id", "country_code"),
    )

    def __repr__(self) -> str:
        return f"<Monitor id={self.id} product_id={self.product_id} country={self.country_code}>"


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    store_name: Mapped[str] = mapped_column(String(256), index=True, nullable=False)
    store_domain: Mapped[str] = mapped_column(String(256), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    original_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    condition: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    shipping: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_reputable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    monitor: Mapped["Monitor"] = relationship("Monitor", back_populates="price_records")

    __table_args__ = (
        Index("ix_price_records_monitor_scraped", "monitor_id", "scraped_at"),
    )

    def __repr__(self) -> str:
        return f"<PriceRecord id={self.id} store={self.store_name!r} price={self.price}>"


class PriceAlert(Base):
    __tablename__ = "price_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    monitor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("monitors.id", ondelete="CASCADE"), nullable=False
    )
    alert_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # below_threshold | price_drop | back_in_stock
    threshold_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    monitor: Mapped["Monitor"] = relationship("Monitor", back_populates="alerts")

    def __repr__(self) -> str:
        return f"<PriceAlert id={self.id} type={self.alert_type!r}>"
