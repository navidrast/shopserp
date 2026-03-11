"""API integration tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_list_countries(client: AsyncClient):
    resp = await client.get("/api/countries")
    assert resp.status_code == 200
    countries = resp.json()
    assert len(countries) >= 17
    codes = [c["code"] for c in countries]
    assert "US" in codes
    assert "AU" in codes
    assert "GB" in codes


@pytest.mark.asyncio
async def test_country_stores(client: AsyncClient):
    resp = await client.get("/api/countries/AU/stores")
    assert resp.status_code == 200
    data = resp.json()
    stores = data["stores"] if isinstance(data, dict) else data
    assert len(stores) > 10
    names = [s["name"] for s in stores]
    assert "JB Hi-Fi" in names


@pytest.mark.asyncio
async def test_create_and_list_monitor(client: AsyncClient):
    resp = await client.post("/api/monitors", json={
        "name": "Test Product",
        "query": "iPhone 15 Pro",
        "countries": ["US", "AU"],
        "interval_minutes": 360,
    })
    assert resp.status_code == 201
    product = resp.json()
    assert product["name"] == "Test Product"
    assert len(product["monitors"]) == 2

    resp = await client.get("/api/monitors")
    assert resp.status_code == 200
    monitors = resp.json()
    assert len(monitors) >= 1


@pytest.mark.asyncio
async def test_get_product_detail(client: AsyncClient):
    resp = await client.post("/api/monitors", json={
        "name": "Detail Test",
        "query": "PS5",
        "countries": ["US"],
    })
    product_id = resp.json()["id"]

    resp = await client.get(f"/api/monitors/{product_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_product(client: AsyncClient):
    resp = await client.post("/api/monitors", json={
        "name": "To Delete",
        "query": "delete me",
        "countries": ["US"],
    })
    product_id = resp.json()["id"]

    resp = await client.delete(f"/api/monitors/{product_id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_add_country_to_product(client: AsyncClient):
    resp = await client.post("/api/monitors", json={
        "name": "Country Test",
        "query": "test",
        "countries": ["US"],
    })
    product_id = resp.json()["id"]

    resp = await client.post(f"/api/monitors/{product_id}/countries", json={
        "country_code": "AU",
    })
    assert resp.status_code == 201
    assert resp.json()["country_code"] == "AU"


@pytest.mark.asyncio
async def test_create_alert(client: AsyncClient):
    resp = await client.post("/api/monitors", json={
        "name": "Alert Test",
        "query": "test",
        "countries": ["US"],
    })
    monitor_id = resp.json()["monitors"][0]["id"]

    resp = await client.post(f"/api/monitors/{monitor_id}/alerts", json={
        "alert_type": "below_threshold",
        "threshold_value": 99.99,
    })
    assert resp.status_code == 201
    assert resp.json()["alert_type"] == "below_threshold"


@pytest.mark.asyncio
async def test_not_found(client: AsyncClient):
    resp = await client.get("/api/monitors/99999")
    assert resp.status_code == 404
