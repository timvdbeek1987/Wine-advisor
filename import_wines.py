#!/usr/bin/env python3
"""
Importeer wijnen uit een CSV in je bestaande SQLite-db.
- Negeert rijen met Bottles <= 0
- Probeert kolomnamen slim te herkennen (naam, land, regio, druiven, vintage, prijs, etc.)
- Parseert blends: "Cabernet Sauvignon 60%; Merlot 40%" of "Chardonnay" → gewichten gelijk verdeeld
- Bouwt automatisch een 5D wijnprofiel via engine.build_wine_profile
- Droge run: toont wat er geïmporteerd zal worden; gebruik --commit om echt te schrijven

Gebruik:
  source .venv/bin/activate
  python import_wines.py /path/naar/export-wines.csv                 # droge run
  python import_wines.py /path/naar/export-wines.csv --commit        # schrijf naar DB

Optioneel:
  --encoding utf-16  --sep ';'   (als autodetect niet goed uitkomt)
  --map '{"name":"Wine","region":"Appellation","bottles":"Qty"}'
"""

from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# importeer jouw app-modules
from db import SessionLocal, init_db, Wine
from engine import build_wine_profile

# -------- Helpers: CSV inlezen met autodetect --------
POSSIBLE_ENCODINGS = ["utf-16", "utf-16le", "utf-16be", "utf-8-sig", "utf-8", "latin-1", "cp1252"]

def read_csv_safely(path: Path, encoding: Optional[str]=None, sep: Optional[str]=None) -> Tuple[pd.DataFrame, str, Optional[str]]:
    if encoding or sep:
        df = pd.read_csv(path, encoding=encoding or "utf-8", sep=sep or None, engine="python")
        return df, encoding or "utf-8", sep
    last_err = None
    for enc in POSSIBLE_ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc, sep=None, engine="python")
            return df, enc, None
        except Exception as e:
            last_err = e
    raise last_err

# -------- Kolommapping & extractie --------
DEFAULT_MAP = {
    "name": ["name", "wine", "title", "cuvee", "label"],
    "country": ["country", "land"],
    "region": ["region", "appellation", "regio", "ava"],
    "vintage": ["vintage", "year", "jaargang"],
    "price_eur": ["price", "price (€)", "prijs", "price_eur"],
    "abv": ["abv", "alcohol", "alcohol%","alc", "alc%"],
    "bottles": ["bottles", "bottle", "qty", "quantity", "stock", "count", "aantal"],
    "grapes": ["grapes", "varieties", "cépages", "blend", "druiven", "druif", "cepage"],
    "soil": ["soil", "bodem"],
    "oak_months": ["oak", "oak_months", "barrel", "barrique", "aging", "rijping", "houtrijping"],
    "climate": ["climate", "klimaat"],  # fallback = "temperate"
}

SEP_GRAPES = re.compile(r"[;,/&+]| en | and ", flags=re.IGNORECASE)
PCT = re.compile(r"(\d+(?:\.\d+)?)\s*%")

def norm(s: str) -> str:
    return str(s or "").strip()

def find_col(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    cols = list(df.columns)
    lowered = {c.lower(): c for c in cols}
    for cand in candidates:
        for c in cols:
            if c.lower() == cand.lower():
                return c
        # fuzzy contains
        for lc, orig in lowered.items():
            if cand.lower() in lc:
                return orig
    return None

def parse_number(x) -> Optional[float]:
    if x is None or (isinstance(x, float) and pd.isna(x)): return None
    s = str(x).strip().replace(",", ".")
    s = re.sub(r"[^\d\.]+", "", s)
    try:
        return float(s) if s else None
    except:
        return None

def parse_int(x) -> Optional[int]:
    n = parse_number(x)
    return int(n) if n is not None else None

def parse_grapes(raw: str) -> List[Dict[str, float]]:
    """
    Voorbeelden:
      "Cabernet Sauvignon 60%, Merlot 40%"
      "Chardonnay"
      "Pinot Noir / Chardonnay / Meunier"
    """
    if not raw: return []
    parts = [p.strip() for p in SEP_GRAPES.split(str(raw)) if p.strip()]
    items = []
    total_pct = 0.0
    for p in parts:
        m = PCT.search(p)
        if m:
            pct = float(m.group(1))
            grape = PCT.sub("", p).strip()
            items.append({"variety": grape, "weight": pct/100.0})
            total_pct += pct
        else:
            items.append({"variety": p, "weight": None})
    # vul gewichten aan
    unknowns = [i for i in items if i["weight"] in (None, 0)]
    known_sum = sum(i["weight"] or 0 for i in items)
    remain = max(0.0, 1.0 - known_sum) if known_sum <= 1.0 else 0.0
    if unknowns:
        w = remain/len(unknowns) if remain > 0 else (1.0/len(items))
        for i in unknowns:
            i["weight"] = w
    # normaliseer
    s = sum(i["weight"] for i in items) or 1.0
    for i in items:
        i["weight"] = round(i["weight"]/s, 4)
    return items

def to_wine_record(row: pd.Series, colmap: Dict[str,str]) -> Optional[Dict]:
    name = norm(row.get(colmap.get("name")))
    if not name: 
        return None
    region = norm(row.get(colmap.get("region"))) or None
    country = norm(row.get(colmap.get("country"))) or None  # NB: db heeft geen country-kolom; we negeren die bij opslaan
    vintage = parse_int(row.get(colmap.get("vintage"))) or 0
    price = parse_number(row.get(colmap.get("price_eur")))
    abv = parse_number(row.get(colmap.get("abv")))
    soil = norm(row.get(colmap.get("soil"))) or None
    oak_months = parse_int(row.get(colmap.get("oak_months"))) or 0
    climate = (norm(row.get(colmap.get("climate"))) or "temperate").lower()

    grapes_raw = row.get(colmap.get("grapes"))
    grapes = parse_grapes(grapes_raw) if grapes_raw is not None else []

    # Als geen druiven bekend → single variety "Unknown" 100% (regelengine geeft neutraal profiel)
    if not grapes:
        grapes = [{"variety": "Unknown", "weight": 1.0}]

    return {
        "name": name,
        "region": region or (country or "Unknown"),
        "climate": climate if climate in ("cool","temperate","warm") else "temperate",
        "grapes": grapes,
        "vintage": vintage,
        "soil": soil,
        "oak_months": oak_months,
        "abv": abv,
        "price_eur": price,
        # country wordt NIET opgeslagen in Wine (je schema heeft die kolom niet)
    }

def build_colmap(df: pd.DataFrame, user_map: Optional[Dict[str,str]]) -> Dict[str,str]:
    mapping: Dict[str,str] = {}
    for key, cands in DEFAULT_MAP.items():
        col = None
        if user_map and key in user_map:
            if user_map[key] in df.columns:
                col = user_map[key]
        if not col:
            col = find_col(df, cands)
        if col:
            mapping[key] = col
    return mapping

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=str)
    ap.add_argument("--commit", action="store_true", help="Schrijf naar database")
    ap.add_argument("--encoding", type=str, help="Forceer encoding (bijv. utf-16)")
    ap.add_argument("--sep", type=str, help="Forceer scheidingsteken (bijv. ';')")
    ap.add_argument("--map", type=str, help="JSON kolomnamen mapping, bv: '{\"name\":\"Wine\",\"bottles\":\"Qty\"}'")
    args = ap.parse_args()

    path = Path(args.csv)
    if not path.exists():
        print(f"Bestand niet gevonden: {path}", file=sys.stderr)
        sys.exit(1)

    # CSV lezen
    df, used_enc, used_sep = read_csv_safely(path, encoding=args.encoding, sep=args.sep)
    print(f"[info] CSV geladen met encoding={used_enc} sep={used_sep}")

    # Kolomnamen opschonen
    df.columns = [str(c).strip() for c in df.columns]

    # Mapping bouwen
    user_map = json.loads(args.map) if args.map else None
    colmap = build_colmap(df, user_map)
    print("[info] kolommapping:", colmap)

    # Bottles-kolom zoeken
    bottles_col = colmap.get("bottles")
    if not bottles_col:
        print("[warn] Geen 'Bottles' kolom gevonden; ik ga alles behandelen alsof Bottles=1 (import ALLEEN bij --commit!))")
        df["_Bottles__tmp"] = 1
        bottles_col = "_Bottles__tmp"

    def bottles_val(x):
        try:
            return float(str(x).replace(",", "."))
        except:
            return 0.0

    # Filter op Bottles > 0
    mask = df[bottles_col].apply(bottles_val) > 0
    df_imp = df[mask].copy()
    print(f"[info] {mask.sum()} rijen met {bottles_col} > 0 (van {len(df)} totaal)")

    # Transformeren naar Wine records
    records = []
    for _, row in df_imp.iterrows():
        rec = to_wine_record(row, colmap)
        if rec:
            records.append(rec)

    print(f"[info] {len(records)} rijen converteren naar Wine-records")

    # Droge run: toon 5 voorbeelden
    for i, r in enumerate(records[:5], 1):
        print(f"  ex#{i}: {r['name']} ({r.get('region')}, {r.get('vintage')}) grapes={r['grapes']} price={r.get('price_eur')}")

    if not args.commit:
        print("\n[DRY-RUN] Niet opgeslagen. Run met --commit om te schrijven.")
        sys.exit(0)

    # ECHT opslaan
    init_db()
    db = SessionLocal()
    try:
        inserted = 0
        for r in records:
            prof, conf = build_wine_profile(
                grapes=r["grapes"],
                climate=r["climate"],
                soil=r.get("soil"),
                oak_months=r.get("oak_months") or 0,
                vintage_vs_norm="normal",
            )
            w = Wine(
                name=r["name"],
                region=r.get("region") or "Unknown",
                climate=r["climate"],
                grapes=r["grapes"],
                vintage=int(r.get("vintage") or 0),
                soil=r.get("soil"),
                oak_months=int(r.get("oak_months") or 0),
                abv=r.get("abv"),
                price_eur=r.get("price_eur"),
                profile=prof,
                confidence=conf,
                notes=None,
                sources=None,
            )
            db.add(w)
            inserted += 1
        db.commit()
        print(f"[ok] {inserted} wijnen opgeslagen.")
    finally:
        db.close()

if __name__ == "__main__":
    main()