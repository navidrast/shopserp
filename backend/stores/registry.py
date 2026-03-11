"""Comprehensive registry of reputable retail stores organized by country.

This module provides a curated database of well-known retail stores across
multiple countries, used to filter search results to show only reputable
sources. Each store entry includes domain information, category, and a
tier ranking indicating relative prominence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True, slots=True)
class StoreInfo:
    """Information about a retail store.

    Attributes:
        name: Human-readable display name.
        domain: Primary domain (lowercase, no protocol).
        aliases: Alternative domains, subdomains, or regional variants.
        category: One of "marketplace", "electronics", "department",
            "specialty", "home", "fashion", "grocery", "sports", "office",
            "gaming", "pharmacy", "automotive", "diy".
        tier: Prominence ranking where 1=major, 2=well-known, 3=notable.
    """

    name: str
    domain: str
    aliases: list[str] = field(default_factory=list)
    category: str = "marketplace"
    tier: int = 2


# ---------------------------------------------------------------------------
# Country metadata
# ---------------------------------------------------------------------------

COUNTRY_INFO: dict[str, dict[str, str]] = {
    "US": {
        "name": "United States",
        "currency": "USD",
        "symbol": "$",
        "gl": "us",
        "hl": "en",
    },
    "AU": {
        "name": "Australia",
        "currency": "AUD",
        "symbol": "A$",
        "gl": "au",
        "hl": "en",
    },
    "GB": {
        "name": "United Kingdom",
        "currency": "GBP",
        "symbol": "\u00a3",
        "gl": "uk",
        "hl": "en",
    },
    "DE": {
        "name": "Germany",
        "currency": "EUR",
        "symbol": "\u20ac",
        "gl": "de",
        "hl": "de",
    },
    "JP": {
        "name": "Japan",
        "currency": "JPY",
        "symbol": "\u00a5",
        "gl": "jp",
        "hl": "ja",
    },
    "CA": {
        "name": "Canada",
        "currency": "CAD",
        "symbol": "C$",
        "gl": "ca",
        "hl": "en",
    },
    "FR": {
        "name": "France",
        "currency": "EUR",
        "symbol": "\u20ac",
        "gl": "fr",
        "hl": "fr",
    },
    "IN": {
        "name": "India",
        "currency": "INR",
        "symbol": "\u20b9",
        "gl": "in",
        "hl": "en",
    },
    "NZ": {
        "name": "New Zealand",
        "currency": "NZD",
        "symbol": "NZ$",
        "gl": "nz",
        "hl": "en",
    },
    "SG": {
        "name": "Singapore",
        "currency": "SGD",
        "symbol": "S$",
        "gl": "sg",
        "hl": "en",
    },
    "KR": {
        "name": "South Korea",
        "currency": "KRW",
        "symbol": "\u20a9",
        "gl": "kr",
        "hl": "ko",
    },
    "BR": {
        "name": "Brazil",
        "currency": "BRL",
        "symbol": "R$",
        "gl": "br",
        "hl": "pt-BR",
    },
    "IT": {
        "name": "Italy",
        "currency": "EUR",
        "symbol": "\u20ac",
        "gl": "it",
        "hl": "it",
    },
    "ES": {
        "name": "Spain",
        "currency": "EUR",
        "symbol": "\u20ac",
        "gl": "es",
        "hl": "es",
    },
    "NL": {
        "name": "Netherlands",
        "currency": "EUR",
        "symbol": "\u20ac",
        "gl": "nl",
        "hl": "nl",
    },
    "SE": {
        "name": "Sweden",
        "currency": "SEK",
        "symbol": "kr",
        "gl": "se",
        "hl": "sv",
    },
    "MX": {
        "name": "Mexico",
        "currency": "MXN",
        "symbol": "MX$",
        "gl": "mx",
        "hl": "es",
    },
}

# ---------------------------------------------------------------------------
# Store registries per country
# ---------------------------------------------------------------------------

COUNTRY_STORES: dict[str, list[StoreInfo]] = {
    # ======================================================================
    # US -- United States
    # ======================================================================
    "US": [
        StoreInfo(
            name="Amazon",
            domain="amazon.com",
            aliases=["www.amazon.com", "smile.amazon.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay",
            domain="ebay.com",
            aliases=["www.ebay.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Walmart",
            domain="walmart.com",
            aliases=["www.walmart.com"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Best Buy",
            domain="bestbuy.com",
            aliases=["www.bestbuy.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Target",
            domain="target.com",
            aliases=["www.target.com"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Costco",
            domain="costco.com",
            aliases=["www.costco.com"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Home Depot",
            domain="homedepot.com",
            aliases=["www.homedepot.com"],
            category="home",
            tier=1,
        ),
        StoreInfo(
            name="Lowe's",
            domain="lowes.com",
            aliases=["www.lowes.com"],
            category="home",
            tier=1,
        ),
        StoreInfo(
            name="Newegg",
            domain="newegg.com",
            aliases=["www.newegg.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="B&H Photo",
            domain="bhphotovideo.com",
            aliases=["www.bhphotovideo.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Adorama",
            domain="adorama.com",
            aliases=["www.adorama.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Micro Center",
            domain="microcenter.com",
            aliases=["www.microcenter.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Sam's Club",
            domain="samsclub.com",
            aliases=["www.samsclub.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Macy's",
            domain="macys.com",
            aliases=["www.macys.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Nordstrom",
            domain="nordstrom.com",
            aliases=["www.nordstrom.com", "shop.nordstrom.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Kohl's",
            domain="kohls.com",
            aliases=["www.kohls.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="GameStop",
            domain="gamestop.com",
            aliases=["www.gamestop.com"],
            category="gaming",
            tier=2,
        ),
        StoreInfo(
            name="Staples",
            domain="staples.com",
            aliases=["www.staples.com"],
            category="office",
            tier=2,
        ),
        StoreInfo(
            name="Office Depot",
            domain="officedepot.com",
            aliases=["www.officedepot.com"],
            category="office",
            tier=2,
        ),
        StoreInfo(
            name="Wayfair",
            domain="wayfair.com",
            aliases=["www.wayfair.com"],
            category="home",
            tier=2,
        ),
        StoreInfo(
            name="Overstock",
            domain="overstock.com",
            aliases=["www.overstock.com"],
            category="home",
            tier=2,
        ),
        StoreInfo(
            name="Zappos",
            domain="zappos.com",
            aliases=["www.zappos.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Chewy",
            domain="chewy.com",
            aliases=["www.chewy.com"],
            category="specialty",
            tier=2,
        ),
        StoreInfo(
            name="REI",
            domain="rei.com",
            aliases=["www.rei.com"],
            category="sports",
            tier=2,
        ),
        StoreInfo(
            name="Dick's Sporting Goods",
            domain="dickssportinggoods.com",
            aliases=["www.dickssportinggoods.com"],
            category="sports",
            tier=2,
        ),
        StoreInfo(
            name="Nike",
            domain="nike.com",
            aliases=["www.nike.com", "store.nike.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Adidas",
            domain="adidas.com",
            aliases=["www.adidas.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Apple Store",
            domain="apple.com",
            aliases=["www.apple.com", "store.apple.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Dell",
            domain="dell.com",
            aliases=["www.dell.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="HP",
            domain="hp.com",
            aliases=["www.hp.com", "store.hp.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Lenovo",
            domain="lenovo.com",
            aliases=["www.lenovo.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Samsung",
            domain="samsung.com",
            aliases=["www.samsung.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Google Store",
            domain="store.google.com",
            aliases=["fi.google.com"],
            category="electronics",
            tier=2,
        ),
    ],
    # ======================================================================
    # AU -- Australia
    # ======================================================================
    "AU": [
        StoreInfo(
            name="Amazon AU",
            domain="amazon.com.au",
            aliases=["www.amazon.com.au"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay AU",
            domain="ebay.com.au",
            aliases=["www.ebay.com.au"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="JB Hi-Fi",
            domain="jbhifi.com.au",
            aliases=["www.jbhifi.com.au"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Harvey Norman",
            domain="harveynorman.com.au",
            aliases=["www.harveynorman.com.au"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Officeworks",
            domain="officeworks.com.au",
            aliases=["www.officeworks.com.au"],
            category="office",
            tier=1,
        ),
        StoreInfo(
            name="Kogan",
            domain="kogan.com",
            aliases=["www.kogan.com", "kogan.com.au"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="The Good Guys",
            domain="thegoodguys.com.au",
            aliases=["www.thegoodguys.com.au"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Catch",
            domain="catch.com.au",
            aliases=["www.catch.com.au"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Myer",
            domain="myer.com.au",
            aliases=["www.myer.com.au"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="David Jones",
            domain="davidjones.com",
            aliases=["www.davidjones.com", "davidjones.com.au"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Big W",
            domain="bigw.com.au",
            aliases=["www.bigw.com.au"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Kmart AU",
            domain="kmart.com.au",
            aliases=["www.kmart.com.au"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Target AU",
            domain="target.com.au",
            aliases=["www.target.com.au"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Bunnings",
            domain="bunnings.com.au",
            aliases=["www.bunnings.com.au"],
            category="diy",
            tier=1,
        ),
        StoreInfo(
            name="Chemist Warehouse",
            domain="chemistwarehouse.com.au",
            aliases=["www.chemistwarehouse.com.au"],
            category="pharmacy",
            tier=2,
        ),
        StoreInfo(
            name="Bing Lee",
            domain="binglee.com.au",
            aliases=["www.binglee.com.au"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Scorptec",
            domain="scorptec.com.au",
            aliases=["www.scorptec.com.au"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="PC Case Gear",
            domain="pccasegear.com",
            aliases=["www.pccasegear.com"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="PLE Computers",
            domain="ple.com.au",
            aliases=["www.ple.com.au"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Centre Com",
            domain="centrecom.com.au",
            aliases=["www.centrecom.com.au"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Woolworths",
            domain="woolworths.com.au",
            aliases=["www.woolworths.com.au"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="Coles",
            domain="coles.com.au",
            aliases=["www.coles.com.au", "shop.coles.com.au"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="Dan Murphy's",
            domain="danmurphys.com.au",
            aliases=["www.danmurphys.com.au"],
            category="specialty",
            tier=2,
        ),
        StoreInfo(
            name="Appliances Online",
            domain="appliancesonline.com.au",
            aliases=["www.appliancesonline.com.au"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="The Iconic",
            domain="theiconic.com.au",
            aliases=["www.theiconic.com.au"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Rebel Sport",
            domain="rebelsport.com.au",
            aliases=["www.rebelsport.com.au"],
            category="sports",
            tier=2,
        ),
    ],
    # ======================================================================
    # GB -- United Kingdom
    # ======================================================================
    "GB": [
        StoreInfo(
            name="Amazon UK",
            domain="amazon.co.uk",
            aliases=["www.amazon.co.uk"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay UK",
            domain="ebay.co.uk",
            aliases=["www.ebay.co.uk"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Argos",
            domain="argos.co.uk",
            aliases=["www.argos.co.uk"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Currys",
            domain="currys.co.uk",
            aliases=["www.currys.co.uk"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="John Lewis",
            domain="johnlewis.com",
            aliases=["www.johnlewis.com"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Tesco",
            domain="tesco.com",
            aliases=["www.tesco.com", "groceries.tesco.com"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="ASDA",
            domain="asda.com",
            aliases=["www.asda.com", "groceries.asda.com"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="Sainsbury's",
            domain="sainsburys.co.uk",
            aliases=["www.sainsburys.co.uk"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="Very",
            domain="very.co.uk",
            aliases=["www.very.co.uk"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="AO.com",
            domain="ao.com",
            aliases=["www.ao.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Maplin",
            domain="maplin.co.uk",
            aliases=["www.maplin.co.uk"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Scan",
            domain="scan.co.uk",
            aliases=["www.scan.co.uk"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Ebuyer",
            domain="ebuyer.com",
            aliases=["www.ebuyer.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Overclockers UK",
            domain="overclockers.co.uk",
            aliases=["www.overclockers.co.uk"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Box",
            domain="box.co.uk",
            aliases=["www.box.co.uk"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Amazon Warehouse",
            domain="amazon.co.uk",
            aliases=["www.amazon.co.uk/warehouse"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Halfords",
            domain="halfords.com",
            aliases=["www.halfords.com"],
            category="automotive",
            tier=2,
        ),
        StoreInfo(
            name="Boots",
            domain="boots.com",
            aliases=["www.boots.com"],
            category="pharmacy",
            tier=1,
        ),
        StoreInfo(
            name="Superdrug",
            domain="superdrug.com",
            aliases=["www.superdrug.com"],
            category="pharmacy",
            tier=2,
        ),
        StoreInfo(
            name="Next",
            domain="next.co.uk",
            aliases=["www.next.co.uk"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="ASOS",
            domain="asos.com",
            aliases=["www.asos.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Sports Direct",
            domain="sportsdirect.com",
            aliases=["www.sportsdirect.com"],
            category="sports",
            tier=2,
        ),
        StoreInfo(
            name="Screwfix",
            domain="screwfix.com",
            aliases=["www.screwfix.com"],
            category="diy",
            tier=2,
        ),
        StoreInfo(
            name="B&Q",
            domain="diy.com",
            aliases=["www.diy.com", "www.bandq.com"],
            category="diy",
            tier=2,
        ),
        StoreInfo(
            name="Carphone Warehouse",
            domain="carphonewarehouse.com",
            aliases=["www.carphonewarehouse.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Laptops Direct",
            domain="laptopsdirect.co.uk",
            aliases=["www.laptopsdirect.co.uk"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="CCL Computers",
            domain="cclonline.com",
            aliases=["www.cclonline.com"],
            category="electronics",
            tier=3,
        ),
    ],
    # ======================================================================
    # DE -- Germany
    # ======================================================================
    "DE": [
        StoreInfo(
            name="Amazon DE",
            domain="amazon.de",
            aliases=["www.amazon.de"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay DE",
            domain="ebay.de",
            aliases=["www.ebay.de"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="MediaMarkt",
            domain="mediamarkt.de",
            aliases=["www.mediamarkt.de"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Saturn",
            domain="saturn.de",
            aliases=["www.saturn.de"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Otto",
            domain="otto.de",
            aliases=["www.otto.de"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Alternate",
            domain="alternate.de",
            aliases=["www.alternate.de"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Cyberport",
            domain="cyberport.de",
            aliases=["www.cyberport.de"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Notebooksbilliger",
            domain="notebooksbilliger.de",
            aliases=["www.notebooksbilliger.de"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Mindfactory",
            domain="mindfactory.de",
            aliases=["www.mindfactory.de"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Thomann",
            domain="thomann.de",
            aliases=["www.thomann.de"],
            category="specialty",
            tier=2,
        ),
        StoreInfo(
            name="Conrad",
            domain="conrad.de",
            aliases=["www.conrad.de"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Galaxus",
            domain="galaxus.de",
            aliases=["www.galaxus.de"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Kaufland",
            domain="kaufland.de",
            aliases=["www.kaufland.de"],
            category="grocery",
            tier=2,
        ),
        StoreInfo(
            name="Lidl",
            domain="lidl.de",
            aliases=["www.lidl.de"],
            category="grocery",
            tier=2,
        ),
        StoreInfo(
            name="Real",
            domain="real.de",
            aliases=["www.real.de"],
            category="grocery",
            tier=3,
        ),
        StoreInfo(
            name="About You",
            domain="aboutyou.de",
            aliases=["www.aboutyou.de"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Zalando",
            domain="zalando.de",
            aliases=["www.zalando.de"],
            category="fashion",
            tier=1,
        ),
        StoreInfo(
            name="IKEA DE",
            domain="ikea.com/de",
            aliases=["www.ikea.com/de"],
            category="home",
            tier=1,
        ),
        StoreInfo(
            name="Hornbach",
            domain="hornbach.de",
            aliases=["www.hornbach.de"],
            category="diy",
            tier=2,
        ),
        StoreInfo(
            name="Bauhaus",
            domain="bauhaus.info",
            aliases=["www.bauhaus.info"],
            category="diy",
            tier=2,
        ),
    ],
    # ======================================================================
    # JP -- Japan
    # ======================================================================
    "JP": [
        StoreInfo(
            name="Amazon JP",
            domain="amazon.co.jp",
            aliases=["www.amazon.co.jp"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Rakuten",
            domain="rakuten.co.jp",
            aliases=["www.rakuten.co.jp", "search.rakuten.co.jp"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Yahoo Shopping JP",
            domain="shopping.yahoo.co.jp",
            aliases=["store.shopping.yahoo.co.jp"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Yodobashi",
            domain="yodobashi.com",
            aliases=["www.yodobashi.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Bic Camera",
            domain="biccamera.com",
            aliases=["www.biccamera.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Kakaku",
            domain="kakaku.com",
            aliases=["www.kakaku.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Joshin",
            domain="joshinweb.jp",
            aliases=["www.joshinweb.jp"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Nojima",
            domain="nojima.co.jp",
            aliases=["www.nojima.co.jp", "online.nojima.co.jp"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Yamada Denki",
            domain="yamada-denkiweb.com",
            aliases=["www.yamada-denkiweb.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Sofmap",
            domain="sofmap.com",
            aliases=["www.sofmap.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Tsukumo",
            domain="tsukumo.co.jp",
            aliases=["www.tsukumo.co.jp", "shop.tsukumo.co.jp"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Dospara",
            domain="dospara.co.jp",
            aliases=["www.dospara.co.jp"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="PC Koubou",
            domain="pc-koubou.jp",
            aliases=["www.pc-koubou.jp"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Kojima",
            domain="kojima.net",
            aliases=["www.kojima.net"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Edion",
            domain="edion.com",
            aliases=["www.edion.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="K's Denki",
            domain="ksdenki.com",
            aliases=["www.ksdenki.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Mercari",
            domain="mercari.com",
            aliases=["www.mercari.com", "jp.mercari.com"],
            category="marketplace",
            tier=2,
        ),
    ],
    # ======================================================================
    # CA -- Canada
    # ======================================================================
    "CA": [
        StoreInfo(
            name="Amazon CA",
            domain="amazon.ca",
            aliases=["www.amazon.ca"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay CA",
            domain="ebay.ca",
            aliases=["www.ebay.ca"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Best Buy CA",
            domain="bestbuy.ca",
            aliases=["www.bestbuy.ca"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Canada Computers",
            domain="canadacomputers.com",
            aliases=["www.canadacomputers.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Newegg CA",
            domain="newegg.ca",
            aliases=["www.newegg.ca"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Staples CA",
            domain="staples.ca",
            aliases=["www.staples.ca"],
            category="office",
            tier=2,
        ),
        StoreInfo(
            name="The Source",
            domain="thesource.ca",
            aliases=["www.thesource.ca"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Walmart CA",
            domain="walmart.ca",
            aliases=["www.walmart.ca"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Costco CA",
            domain="costco.ca",
            aliases=["www.costco.ca"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Memory Express",
            domain="memoryexpress.com",
            aliases=["www.memoryexpress.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Mike's Computer Shop",
            domain="mikescomputershop.com",
            aliases=["www.mikescomputershop.com"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="London Drugs",
            domain="londondrugs.com",
            aliases=["www.londondrugs.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Canadian Tire",
            domain="canadiantire.ca",
            aliases=["www.canadiantire.ca"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Hudson's Bay",
            domain="thebay.com",
            aliases=["www.thebay.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Shoppers Drug Mart",
            domain="shoppersdrugmart.ca",
            aliases=["www.shoppersdrugmart.ca"],
            category="pharmacy",
            tier=2,
        ),
    ],
    # ======================================================================
    # FR -- France
    # ======================================================================
    "FR": [
        StoreInfo(
            name="Amazon FR",
            domain="amazon.fr",
            aliases=["www.amazon.fr"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Cdiscount",
            domain="cdiscount.com",
            aliases=["www.cdiscount.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Fnac",
            domain="fnac.com",
            aliases=["www.fnac.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Darty",
            domain="darty.com",
            aliases=["www.darty.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Boulanger",
            domain="boulanger.com",
            aliases=["www.boulanger.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="LDLC",
            domain="ldlc.com",
            aliases=["www.ldlc.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Rue du Commerce",
            domain="rueducommerce.fr",
            aliases=["www.rueducommerce.fr"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Materiel.net",
            domain="materiel.net",
            aliases=["www.materiel.net"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="GrosBill",
            domain="grosbill.com",
            aliases=["www.grosbill.com"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Top Achat",
            domain="topachat.com",
            aliases=["www.topachat.com"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Cultura",
            domain="cultura.com",
            aliases=["www.cultura.com"],
            category="specialty",
            tier=2,
        ),
        StoreInfo(
            name="Carrefour",
            domain="carrefour.fr",
            aliases=["www.carrefour.fr"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="Leclerc",
            domain="e.leclerc",
            aliases=["www.e.leclerc"],
            category="grocery",
            tier=1,
        ),
        StoreInfo(
            name="Auchan",
            domain="auchan.fr",
            aliases=["www.auchan.fr"],
            category="grocery",
            tier=2,
        ),
        StoreInfo(
            name="La Redoute",
            domain="laredoute.fr",
            aliases=["www.laredoute.fr"],
            category="fashion",
            tier=2,
        ),
    ],
    # ======================================================================
    # IN -- India
    # ======================================================================
    "IN": [
        StoreInfo(
            name="Amazon IN",
            domain="amazon.in",
            aliases=["www.amazon.in"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Flipkart",
            domain="flipkart.com",
            aliases=["www.flipkart.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Myntra",
            domain="myntra.com",
            aliases=["www.myntra.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Snapdeal",
            domain="snapdeal.com",
            aliases=["www.snapdeal.com"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Tata CLiQ",
            domain="tatacliq.com",
            aliases=["www.tatacliq.com"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Croma",
            domain="croma.com",
            aliases=["www.croma.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Reliance Digital",
            domain="reliancedigital.in",
            aliases=["www.reliancedigital.in"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Vijay Sales",
            domain="vijaysales.com",
            aliases=["www.vijaysales.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Paytm Mall",
            domain="paytmmall.com",
            aliases=["www.paytmmall.com"],
            category="marketplace",
            tier=3,
        ),
        StoreInfo(
            name="JioMart",
            domain="jiomart.com",
            aliases=["www.jiomart.com"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Nykaa",
            domain="nykaa.com",
            aliases=["www.nykaa.com"],
            category="specialty",
            tier=2,
        ),
        StoreInfo(
            name="Ajio",
            domain="ajio.com",
            aliases=["www.ajio.com"],
            category="fashion",
            tier=2,
        ),
        StoreInfo(
            name="Meesho",
            domain="meesho.com",
            aliases=["www.meesho.com"],
            category="marketplace",
            tier=2,
        ),
    ],
    # ======================================================================
    # NZ -- New Zealand
    # ======================================================================
    "NZ": [
        StoreInfo(
            name="Amazon (ships to NZ)",
            domain="amazon.com",
            aliases=["www.amazon.com"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="PB Tech",
            domain="pbtech.co.nz",
            aliases=["www.pbtech.co.nz"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Mighty Ape",
            domain="mightyape.co.nz",
            aliases=["www.mightyape.co.nz"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Noel Leeming",
            domain="noelleeming.co.nz",
            aliases=["www.noelleeming.co.nz"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Harvey Norman NZ",
            domain="harveynorman.co.nz",
            aliases=["www.harveynorman.co.nz"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="JB Hi-Fi NZ",
            domain="jbhifi.co.nz",
            aliases=["www.jbhifi.co.nz"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Warehouse Stationery",
            domain="warehousestationery.co.nz",
            aliases=["www.warehousestationery.co.nz"],
            category="office",
            tier=2,
        ),
        StoreInfo(
            name="The Warehouse",
            domain="thewarehouse.co.nz",
            aliases=["www.thewarehouse.co.nz"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Computer Lounge",
            domain="computerlounge.co.nz",
            aliases=["www.computerlounge.co.nz"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Playtech",
            domain="playtech.co.nz",
            aliases=["www.playtech.co.nz"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Farmers",
            domain="farmers.co.nz",
            aliases=["www.farmers.co.nz"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Briscoes",
            domain="briscoes.co.nz",
            aliases=["www.briscoes.co.nz"],
            category="home",
            tier=2,
        ),
    ],
    # ======================================================================
    # SG -- Singapore
    # ======================================================================
    "SG": [
        StoreInfo(
            name="Amazon SG",
            domain="amazon.sg",
            aliases=["www.amazon.sg"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Lazada SG",
            domain="lazada.sg",
            aliases=["www.lazada.sg"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Shopee SG",
            domain="shopee.sg",
            aliases=["www.shopee.sg"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Courts",
            domain="courts.com.sg",
            aliases=["www.courts.com.sg"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Challenger",
            domain="challenger.sg",
            aliases=["www.challenger.sg"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Harvey Norman SG",
            domain="harveynorman.com.sg",
            aliases=["www.harveynorman.com.sg"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Best Denki",
            domain="bestdenki.com.sg",
            aliases=["www.bestdenki.com.sg"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Gain City",
            domain="gaincity.com",
            aliases=["www.gaincity.com"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Qoo10",
            domain="qoo10.sg",
            aliases=["www.qoo10.sg"],
            category="marketplace",
            tier=2,
        ),
    ],
    # ======================================================================
    # KR -- South Korea
    # ======================================================================
    "KR": [
        StoreInfo(
            name="Coupang",
            domain="coupang.com",
            aliases=["www.coupang.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Gmarket",
            domain="gmarket.co.kr",
            aliases=["www.gmarket.co.kr"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="11st",
            domain="11st.co.kr",
            aliases=["www.11st.co.kr"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Auction",
            domain="auction.co.kr",
            aliases=["www.auction.co.kr"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Naver Shopping",
            domain="shopping.naver.com",
            aliases=["search.shopping.naver.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="SSG",
            domain="ssg.com",
            aliases=["www.ssg.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Lotte ON",
            domain="lotteon.com",
            aliases=["www.lotteon.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Tmon",
            domain="tmon.co.kr",
            aliases=["www.tmon.co.kr"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="WeMakePrice",
            domain="wemakeprice.com",
            aliases=["www.wemakeprice.com"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Danawa",
            domain="danawa.com",
            aliases=["www.danawa.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Interpark",
            domain="interpark.com",
            aliases=["www.interpark.com"],
            category="marketplace",
            tier=2,
        ),
    ],
    # ======================================================================
    # BR -- Brazil
    # ======================================================================
    "BR": [
        StoreInfo(
            name="Amazon BR",
            domain="amazon.com.br",
            aliases=["www.amazon.com.br"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Mercado Livre",
            domain="mercadolivre.com.br",
            aliases=["www.mercadolivre.com.br"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Magazine Luiza",
            domain="magazineluiza.com.br",
            aliases=["www.magazineluiza.com.br"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Americanas",
            domain="americanas.com.br",
            aliases=["www.americanas.com.br"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Casas Bahia",
            domain="casasbahia.com.br",
            aliases=["www.casasbahia.com.br"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Submarino",
            domain="submarino.com.br",
            aliases=["www.submarino.com.br"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Kabum",
            domain="kabum.com.br",
            aliases=["www.kabum.com.br"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Pichau",
            domain="pichau.com.br",
            aliases=["www.pichau.com.br"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="TerabyteShop",
            domain="terabyteshop.com.br",
            aliases=["www.terabyteshop.com.br"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Extra",
            domain="extra.com.br",
            aliases=["www.extra.com.br"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Shoptime",
            domain="shoptime.com.br",
            aliases=["www.shoptime.com.br"],
            category="marketplace",
            tier=3,
        ),
    ],
    # ======================================================================
    # IT -- Italy
    # ======================================================================
    "IT": [
        StoreInfo(
            name="Amazon IT",
            domain="amazon.it",
            aliases=["www.amazon.it"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay IT",
            domain="ebay.it",
            aliases=["www.ebay.it"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="MediaWorld",
            domain="mediaworld.it",
            aliases=["www.mediaworld.it"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Unieuro",
            domain="unieuro.it",
            aliases=["www.unieuro.it"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="ePrice",
            domain="eprice.it",
            aliases=["www.eprice.it"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Monclick",
            domain="monclick.it",
            aliases=["www.monclick.it"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Euronics",
            domain="euronics.it",
            aliases=["www.euronics.it"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Trovaprezzi",
            domain="trovaprezzi.it",
            aliases=["www.trovaprezzi.it"],
            category="marketplace",
            tier=2,
        ),
    ],
    # ======================================================================
    # ES -- Spain
    # ======================================================================
    "ES": [
        StoreInfo(
            name="Amazon ES",
            domain="amazon.es",
            aliases=["www.amazon.es"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="eBay ES",
            domain="ebay.es",
            aliases=["www.ebay.es"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="El Corte Ingles",
            domain="elcorteingles.es",
            aliases=["www.elcorteingles.es"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="PcComponentes",
            domain="pccomponentes.com",
            aliases=["www.pccomponentes.com"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="MediaMarkt ES",
            domain="mediamarkt.es",
            aliases=["www.mediamarkt.es"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Fnac ES",
            domain="fnac.es",
            aliases=["www.fnac.es"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Carrefour ES",
            domain="carrefour.es",
            aliases=["www.carrefour.es"],
            category="grocery",
            tier=2,
        ),
        StoreInfo(
            name="Worten",
            domain="worten.es",
            aliases=["www.worten.es"],
            category="electronics",
            tier=2,
        ),
    ],
    # ======================================================================
    # NL -- Netherlands
    # ======================================================================
    "NL": [
        StoreInfo(
            name="Amazon NL",
            domain="amazon.nl",
            aliases=["www.amazon.nl"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Bol.com",
            domain="bol.com",
            aliases=["www.bol.com"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Coolblue",
            domain="coolblue.nl",
            aliases=["www.coolblue.nl"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="MediaMarkt NL",
            domain="mediamarkt.nl",
            aliases=["www.mediamarkt.nl"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="Alternate NL",
            domain="alternate.nl",
            aliases=["www.alternate.nl"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Azerty",
            domain="azerty.nl",
            aliases=["www.azerty.nl"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Megekko",
            domain="megekko.nl",
            aliases=["www.megekko.nl"],
            category="electronics",
            tier=3,
        ),
        StoreInfo(
            name="Tweakers",
            domain="tweakers.net",
            aliases=["www.tweakers.net"],
            category="electronics",
            tier=2,
        ),
    ],
    # ======================================================================
    # SE -- Sweden
    # ======================================================================
    "SE": [
        StoreInfo(
            name="Amazon SE",
            domain="amazon.se",
            aliases=["www.amazon.se"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Inet",
            domain="inet.se",
            aliases=["www.inet.se"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Komplett",
            domain="komplett.se",
            aliases=["www.komplett.se"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Dustin",
            domain="dustin.se",
            aliases=["www.dustin.se"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="NetOnNet",
            domain="netonnet.se",
            aliases=["www.netonnet.se"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Elgiganten",
            domain="elgiganten.se",
            aliases=["www.elgiganten.se"],
            category="electronics",
            tier=1,
        ),
        StoreInfo(
            name="MediaMarkt SE",
            domain="mediamarkt.se",
            aliases=["www.mediamarkt.se"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="CDON",
            domain="cdon.se",
            aliases=["www.cdon.se"],
            category="marketplace",
            tier=2,
        ),
        StoreInfo(
            name="Webhallen",
            domain="webhallen.com",
            aliases=["www.webhallen.com"],
            category="electronics",
            tier=2,
        ),
    ],
    # ======================================================================
    # MX -- Mexico
    # ======================================================================
    "MX": [
        StoreInfo(
            name="Amazon MX",
            domain="amazon.com.mx",
            aliases=["www.amazon.com.mx"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Mercado Libre MX",
            domain="mercadolibre.com.mx",
            aliases=["www.mercadolibre.com.mx"],
            category="marketplace",
            tier=1,
        ),
        StoreInfo(
            name="Liverpool",
            domain="liverpool.com.mx",
            aliases=["www.liverpool.com.mx"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Coppel",
            domain="coppel.com",
            aliases=["www.coppel.com"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Elektra",
            domain="elektra.com.mx",
            aliases=["www.elektra.com.mx"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Best Buy MX",
            domain="bestbuy.com.mx",
            aliases=["www.bestbuy.com.mx"],
            category="electronics",
            tier=2,
        ),
        StoreInfo(
            name="Sears MX",
            domain="sears.com.mx",
            aliases=["www.sears.com.mx"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Office Depot MX",
            domain="officedepot.com.mx",
            aliases=["www.officedepot.com.mx"],
            category="office",
            tier=2,
        ),
        StoreInfo(
            name="Walmart MX",
            domain="walmart.com.mx",
            aliases=["www.walmart.com.mx"],
            category="department",
            tier=1,
        ),
        StoreInfo(
            name="Sanborns",
            domain="sanborns.com.mx",
            aliases=["www.sanborns.com.mx"],
            category="department",
            tier=2,
        ),
        StoreInfo(
            name="Palacio de Hierro",
            domain="elpalaciodehierro.com",
            aliases=["www.elpalaciodehierro.com"],
            category="department",
            tier=2,
        ),
    ],
}

# ---------------------------------------------------------------------------
# Pre-computed lookup indexes (built once at import time)
# ---------------------------------------------------------------------------

# Maps every known domain (primary + aliases) to (store_name, country_code).
_DOMAIN_INDEX: dict[str, tuple[str, str]] = {}

# Set of all reputable primary domains and aliases.
_ALL_DOMAINS: set[str] = set()


def _build_indexes() -> None:
    """Build internal lookup indexes from COUNTRY_STORES."""
    for country_code, stores in COUNTRY_STORES.items():
        for store in stores:
            primary = store.domain.lower()
            _DOMAIN_INDEX[primary] = (store.name, country_code)
            _ALL_DOMAINS.add(primary)
            for alias in store.aliases:
                alias_lower = alias.lower()
                # Only set if not already claimed by a primary domain.
                if alias_lower not in _DOMAIN_INDEX:
                    _DOMAIN_INDEX[alias_lower] = (store.name, country_code)
                _ALL_DOMAINS.add(alias_lower)


_build_indexes()

# ---------------------------------------------------------------------------
# Public helper functions
# ---------------------------------------------------------------------------


def get_stores_for_country(country_code: str) -> list[StoreInfo]:
    """Return all registered stores for a given 2-letter country code.

    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "AU").

    Returns:
        List of StoreInfo objects for that country, or empty list if unknown.
    """
    return COUNTRY_STORES.get(country_code.upper(), [])


def is_reputable_store(domain: str, country_code: str) -> bool:
    """Check whether a domain belongs to a reputable store in a given country.

    The check is performed against both primary domains and aliases for the
    specified country. The match is case-insensitive.

    Args:
        domain: Domain to check (e.g., "amazon.com.au").
        country_code: ISO 3166-1 alpha-2 country code.

    Returns:
        True if the domain belongs to a known store in that country.
    """
    domain_lower = domain.lower().removeprefix("www.")
    country_upper = country_code.upper()
    stores = COUNTRY_STORES.get(country_upper, [])
    for store in stores:
        if store.domain == domain_lower:
            return True
        # Also check with www. stripped from aliases
        for alias in store.aliases:
            if alias.lower().removeprefix("www.") == domain_lower:
                return True
    return False


def identify_store(domain: str) -> tuple[str, bool]:
    """Identify a store by its domain across all countries.

    Looks up the domain (and its ``www.``-stripped variant) in the global
    index of all registered domains.

    Args:
        domain: Domain to identify (e.g., "jbhifi.com.au").

    Returns:
        A tuple of ``(store_name, is_reputable)``.  If the domain is not
        found, returns ``("Unknown", False)``.
    """
    domain_lower = domain.lower()
    entry = _DOMAIN_INDEX.get(domain_lower)
    if entry is not None:
        return entry[0], True

    # Try stripping www. prefix
    stripped = domain_lower.removeprefix("www.")
    if stripped != domain_lower:
        entry = _DOMAIN_INDEX.get(stripped)
        if entry is not None:
            return entry[0], True

    return "Unknown", False


def get_supported_countries() -> list[dict[str, str | int]]:
    """Return metadata for all supported countries.

    Returns:
        A list of dicts, each containing ``code``, ``name``, ``currency``,
        and ``stores_count`` keys.
    """
    result: list[dict[str, str | int]] = []
    for code, info in COUNTRY_INFO.items():
        stores = COUNTRY_STORES.get(code, [])
        result.append(
            {
                "code": code,
                "name": info["name"],
                "currency": info["currency"],
                "stores_count": len(stores),
            }
        )
    return result


def get_all_reputable_domains() -> set[str]:
    """Return the complete set of known reputable domains across all countries.

    This includes both primary domains and all aliases, all lowercased.

    Returns:
        A set of domain strings.
    """
    return set(_ALL_DOMAINS)


def get_stores_by_tier(
    country_code: str, max_tier: int = 2
) -> list[StoreInfo]:
    """Return stores for a country filtered by tier.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.
        max_tier: Maximum tier to include (1=major only, 2=major+well-known,
            3=all).

    Returns:
        Filtered list of StoreInfo objects.
    """
    return [
        store
        for store in get_stores_for_country(country_code)
        if store.tier <= max_tier
    ]


def get_stores_by_category(
    country_code: str, category: str
) -> list[StoreInfo]:
    """Return stores for a country filtered by category.

    Args:
        country_code: ISO 3166-1 alpha-2 country code.
        category: Category string (e.g., "electronics", "marketplace").

    Returns:
        Filtered list of StoreInfo objects matching the category.
    """
    cat_lower = category.lower()
    return [
        store
        for store in get_stores_for_country(country_code)
        if store.category == cat_lower
    ]


def find_store_country(domain: str) -> Optional[str]:
    """Find which country a store domain belongs to.

    Args:
        domain: Domain to look up.

    Returns:
        The 2-letter country code, or None if not found.
    """
    domain_lower = domain.lower().removeprefix("www.")
    entry = _DOMAIN_INDEX.get(domain_lower)
    if entry is not None:
        return entry[1]
    return None
