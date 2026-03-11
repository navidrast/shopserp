"""Store registry unit tests."""

from backend.stores.registry import (
    get_stores_for_country,
    is_reputable_store,
    identify_store,
    get_supported_countries,
    get_all_reputable_domains,
    COUNTRY_INFO,
)


def test_supported_countries():
    countries = get_supported_countries()
    assert len(countries) >= 17
    codes = {c["code"] for c in countries}
    for expected in ["US", "AU", "GB", "DE", "JP", "CA", "FR", "IN", "NZ", "SG", "KR", "BR"]:
        assert expected in codes


def test_country_info():
    assert "US" in COUNTRY_INFO
    assert COUNTRY_INFO["US"]["currency"] == "USD"
    assert COUNTRY_INFO["AU"]["currency"] == "AUD"
    assert COUNTRY_INFO["JP"]["currency"] == "JPY"


def test_stores_for_country():
    au_stores = get_stores_for_country("AU")
    assert len(au_stores) > 10
    names = [s.name for s in au_stores]
    assert "JB Hi-Fi" in names
    assert "Harvey Norman" in names


def test_reputable_store_check():
    assert is_reputable_store("amazon.com", "US")
    assert is_reputable_store("jbhifi.com.au", "AU")
    assert not is_reputable_store("randomstore123.com", "US")


def test_identify_store():
    name, is_rep = identify_store("bestbuy.com")
    assert is_rep
    assert "Best Buy" in name

    name, is_rep = identify_store("unknown-store.xyz")
    assert not is_rep


def test_all_reputable_domains():
    domains = get_all_reputable_domains()
    assert len(domains) > 100
    assert "amazon.com" in domains
