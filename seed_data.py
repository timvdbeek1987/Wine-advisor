# seed_data.py
from __future__ import annotations
from sqlalchemy.orm import Session
from db import Wine
from engine import build_wine_profile

EXAMPLE_WINES = [
    {
        "name":"Swartland Chenin 'Granite' 2022",
        "region":"Swartland",
        "climate":"warm",
        "grapes":[{"variety":"Chenin Blanc","weight":1.0}],
        "vintage":2022,
        "soil":"granite",
        "oak_months":6,
        "abv":13.0,
        "price_eur":18.95,
        "vintage_vs_norm":"normal",
    },
    {
        "name":"Marlborough Sauvignon Blanc 2023",
        "region":"Marlborough",
        "climate":"cool",
        "grapes":[{"variety":"Sauvignon Blanc","weight":1.0}],
        "vintage":2023,
        "soil":"sand",
        "oak_months":0,
        "abv":12.5,
        "price_eur":12.50,
        "vintage_vs_norm":"normal",
    },
    {
        "name":"Barossa Shiraz Reserve 2021",
        "region":"Barossa",
        "climate":"warm",
        "grapes":[{"variety":"Syrah","weight":1.0}],
        "vintage":2021,
        "soil":"clay",
        "oak_months":20,
        "abv":14.5,
        "price_eur":29.90,
        "vintage_vs_norm":"warmer",
    },
    {
        "name":"Limestone Coast Pinot Noir 2022",
        "region":"Limestone Coast",
        "climate":"cool",
        "grapes":[{"variety":"Pinot Noir","weight":1.0}],
        "vintage":2022,
        "soil":"limestone",
        "oak_months":0,
        "abv":13.0,
        "price_eur":22.00,
        "vintage_vs_norm":"cooler",
    },
    {
        "name":"Left Bank Cabernet 2020",
        "region":"Bordeaux Left Bank",
        "climate":"moderate",
        "grapes":[{"variety":"Cabernet Sauvignon","weight":0.7},{"variety":"Merlot","weight":0.3}],
        "vintage":2020,
        "soil":"gravel",  # onbekend → geen soil-correctie behalve default
        "oak_months":12,
        "abv":13.5,
        "price_eur":34.50,
        "vintage_vs_norm":"normal",
    },
]

def seed(db: Session):
    if db.query(Wine).count() > 0:
        return
    for w in EXAMPLE_WINES:
        prof, conf = build_wine_profile(
            grapes=w["grapes"],
            climate=w["climate"],
            soil=w.get("soil"),
            oak_months=w.get("oak_months",0),
            vintage_vs_norm=w.get("vintage_vs_norm","normal")
        )
        db.add(Wine(
            name=w["name"],
            region=w["region"],
            climate=w["climate"],
            grapes=w["grapes"],
            vintage=w["vintage"],
            soil=w.get("soil"),
            oak_months=w.get("oak_months",0),
            abv=w.get("abv"),
            price_eur=w.get("price_eur"),
            profile=prof,
            confidence=conf
        ))
    db.commit()