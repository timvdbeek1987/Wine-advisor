# app.py
from __future__ import annotations
from typing import Dict, Any, Optional, List, Tuple
from fastapi import FastAPI, Depends, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os

from db import init_db, get_db, Wine
from models import WineIn
from engine import build_wine_profile, build_user_profile, weighted_cosine
from seed_data import seed
from enrichment import enrich_wine  # zorg dat enrichment.py in de root staat

app = FastAPI(title="Intelligente Wijnadvies Tool", version="0.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ---------- Startup ----------
@app.on_event("startup")
def on_startup():
    init_db()

# ---------- Static / UI ----------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root_page():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
def admin_page():
    path = os.path.join(STATIC_DIR, "admin.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>admin.html ontbreekt in /static</h1>", status_code=500)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# Detailpagina voor één wijn
@app.get("/admin/wine/{wine_id}", response_class=HTMLResponse, include_in_schema=False)
def wine_detail_page(wine_id: int):
    path = os.path.join(STATIC_DIR, "wine.html")
    if not os.path.exists(path):
        return HTMLResponse("<h1>wine.html ontbreekt in /static</h1>", status_code=500)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().replace("{{WINE_ID}}", str(wine_id))

@app.get("/static/{path:path}", include_in_schema=False)
def static_files(path: str):
    full = os.path.join(STATIC_DIR, path)
    if not os.path.exists(full):
        raise HTTPException(404, f"Bestand niet gevonden: {path}")
    return FileResponse(full)

# ---------- Quiz ----------
QUIZ = [
    {"id":"Q1","title":"Wat is jouw ‘baseline’ voor drankjes?",
     "options":[
         {"id":"A","label":"Fris & dorstlessend (citroen, tonic)"},
         {"id":"B","label":"Licht & fruitig (appel, perzik)"},
         {"id":"C","label":"Vol & rond (mango/choco)"},
         {"id":"D","label":"Kruidig/complex (espresso/bitters)"},
     ]},
    {"id":"Q2","title":"Welke sfeer trekt je het meest?",
     "options":[
         {"id":"A","label":"Zonnig terras aan de kust"},
         {"id":"B","label":"Knisperend haardvuur"},
         {"id":"C","label":"City night out"},
         {"id":"D","label":"Landelijke tafel met goed eten"},
     ]},
    {"id":"Q3","title":"Favoriete borrelhap?",
     "options":[
         {"id":"A","label":"Oesters / citroen"},
         {"id":"B","label":"Oude kaas / charcuterie"},
         {"id":"C","label":"Bruschetta tomaat-basilicum"},
         {"id":"D","label":"Bitterballen / truffelmayo"},
     ]},
    {"id":"Q4","title":"Op een wijnavond wil je vooral…",
     "options":[
         {"id":"A","label":"Iets verfrissends"},
         {"id":"B","label":"Iets zacht & rond"},
         {"id":"C","label":"Iets kruidigs met karakter"},
         {"id":"D","label":"Iets aromatisch & geurig"},
     ]},
    {"id":"Q5","title":"Reismetafoor voor je smaak:",
     "options":[
         {"id":"A","label":"Vertrouwd klassiek (bistro’s)"},
         {"id":"B","label":"Fris en kustachtig"},
         {"id":"C","label":"Rijk & zongekust"},
         {"id":"D","label":"Ruig & avontuurlijk"},
     ]},
    {"id":"Q6","title":"Welke dessert past het meest?",
     "options":[
         {"id":"A","label":"Citroentaart"},
         {"id":"B","label":"Panna cotta / vanille"},
         {"id":"C","label":"Pure chocolade"},
         {"id":"D","label":"Kaasplankje"},
     ]},
    {"id":"Q7","title":"Bij eten zet je wijn in als…",
     "options":[
         {"id":"A","label":"Frisse tegenhanger"},
         {"id":"B","label":"Match in rijkdom"},
         {"id":"C","label":"Aroma-boost"},
         {"id":"D","label":"Solo-sipper"},
     ]},
    {"id":"Q8","title":"Ben je eerder…",
     "options":[
         {"id":"A","label":"Team klassiekers"},
         {"id":"B","label":"Team verkennen"},
         {"id":"C","label":"Mix van beide"},
     ]},
    {"id":"Q9","title":"Structuur in rode wijn?",
     "options":[
         {"id":"A","label":"Zo zacht mogelijk"},
         {"id":"B","label":"Medium grip"},
         {"id":"C","label":"Stevig met tannine"},
         {"id":"D","label":"Ik drink zelden rood"},
     ]},
    {"id":"Q10","title":"Budget & inzet",
     "options":[
         {"id":"A","label":"€8–€12 dagelijks"},
         {"id":"B","label":"€12–€20 kwaliteit/prijs"},
         {"id":"C","label":"€20–€35 bijzonder"},
         {"id":"D","label":"€35+ iconisch"},
     ]},
]

@app.get("/api/quiz")
def get_quiz():
    return {"questions": QUIZ}

# ---------- Heuristiek drinkvenster ----------
def _heuristic_window(
    color: Optional[str],
    grapes: List[Dict[str, Any]],
    climate: Optional[str],
    vintage: Optional[int]
) -> Tuple[Optional[int], Optional[int]]:
    """Geef (from, to) terug; None als onduidelijk."""
    if not vintage:
        vintage = int(os.environ.get("DEFAULT_YEAR", "2025"))
    y = vintage
    color_l = (color or "").lower()
    main_grape = ""
    if grapes:
        # hoofd-druif = hoogste gewicht
        try:
            main = sorted(grapes, key=lambda g: float(g.get("weight") or 0), reverse=True)[0]
            main_grape = (main.get("variety") or "").lower()
        except Exception:
            main_grape = (grapes[0].get("variety") or "").lower()
    climate_l = (climate or "temperate").lower()

    def yrs(miny, maxy): return (y + miny, y + maxy)

    # Baseren op kleur/druif
    if "mousser" in color_l or "spark" in color_l or "champ" in main_grape:
        frm, to = yrs(1, 5)
    elif "rosé" in color_l or "rose" in color_l:
        frm, to = yrs(0, 2)
    elif "wit" in color_l or "white" in color_l:
        if any(k in main_grape for k in ["riesling", "chenin"]):
            frm, to = yrs(2, 10)
        elif "chardonnay" in main_grape:
            frm, to = yrs(1, 8)
        else:
            frm, to = yrs(0, 4)
    else:  # rood
        if any(k in main_grape for k in ["nebbiolo", "cabernet", "syrah", "tempranillo"]):
            frm, to = yrs(3, 15)
        elif any(k in main_grape for k in ["pinot noir", "sangiovese", "grenache", "merlot"]):
            frm, to = yrs(2, 10)
        else:
            frm, to = yrs(1, 6)

    # Klimaat-correctie
    if climate_l == "cool":
        frm = max(frm - 1, y)  # iets vroeger toegankelijk
    elif climate_l == "warm":
        to = to - 1             # iets korter topvenster

    return (frm, to)

# ---------- Wines (list + add) ----------
@app.get("/api/wines")
def list_wines(db: Session = Depends(get_db)):
    rows = db.query(Wine).all()
    return [{
        "id": w.id,
        "name": w.name,
        "region": w.region,
        "vintage": w.vintage,
        "climate": w.climate,
        "price_eur": getattr(w, "price_eur", None),
        "profile": w.profile,
        "confidence": w.confidence,
        "notes": w.notes,
        "sources": w.sources,
        "bottles": getattr(w, "bottles", None),
    } for w in rows]

@app.post("/api/wines")
def add_wine(w: WineIn, db: Session = Depends(get_db)):
    profile, conf = build_wine_profile(
        grapes=w.grapes,
        climate=w.climate,
        soil=w.soil,
        oak_months=w.oak_months,
        vintage_vs_norm="normal",
    )
    row = Wine(
        name=w.name,
        region=w.region,
        climate=w.climate,
        grapes=w.grapes,
        vintage=w.vintage,
        soil=w.soil,
        oak_months=w.oak_months,
        abv=w.abv,
        price_eur=getattr(w, "price_eur", None),
        profile=profile,
        confidence=conf,
        notes=None,
        sources=None,
        bottles=1,
    )
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "profile": row.profile, "confidence": row.confidence}

# ---------- Seed ----------
@app.post("/api/seed")
def seed_endpoint(db: Session = Depends(get_db)):
    seed(db)
    return {"status": "ok"}

# ---------- Matchen ----------
@app.post("/api/match")
def match(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    Verwacht: {"quiz_answers":[{"question_id":"Q1","option_id":"A"}, ...]}
    """
    answers = payload.get("quiz_answers") or []
    if not isinstance(answers, list) or not answers:
        raise HTTPException(400, "quiz_answers ontbreekt of leeg")

    user_prof = build_user_profile(answers)
    wines = db.query(Wine).all()
    if not wines:
        raise HTTPException(400, "Geen wijnen in database (run /api/seed of voeg wijnen toe).")

    scored = []
    for w in wines:
        sim = float(weighted_cosine(user_prof, w.profile))
        why = "Waarom dit past: " + ("fris & balans" if user_prof["ZB"] >= 60 else "structuur & diepte")
        scored.append({"wine": w, "similarity": sim, "why": why})
    scored.sort(key=lambda x: x["similarity"], reverse=True)
    top3 = scored[:3]

    def serialize(m):
        w = m["wine"]
        return {
            "wine": {
                "id": w.id,
                "name": w.name,
                "region": w.region,
                "price_eur": getattr(w, "price_eur", None),
                "profile": w.profile,
                "confidence": w.confidence,
            },
            "similarity": round(m["similarity"], 4),
            "why": m["why"],
        }

    return {"user_profile": user_prof, "matches": [serialize(x) for x in top3]}

# ---------- Admin: auto-profiel (regels), verrijking ----------
@app.post("/api/admin/auto_profile")
def admin_auto_profile(payload: Dict[str, Any] = Body(...)):
    grapes = payload.get("grapes") or []
    climate = (payload.get("climate") or "temperate").lower()
    soil = payload.get("soil")
    oak = int(payload.get("oak_months") or 0)
    prof, conf = build_wine_profile(
        grapes=grapes, climate=climate, soil=soil, oak_months=oak, vintage_vs_norm="normal"
    )
    return {"profile": prof, "confidence": conf, "notes": "", "sources": []}

@app.post("/api/admin/enrich")
def admin_enrich(payload: Dict[str, Any] = Body(...)):
    grapes = payload.get("grapes") or []
    grape_terms = [g.get("variety", "") for g in grapes if g.get("variety")]
    region = payload.get("region")
    country = payload.get("country")
    vintage = payload.get("vintage")
    color = payload.get("color")
    climate = payload.get("climate")

    data = enrich_wine(grape_terms=grape_terms, region_term=region, country=country, vintage=vintage)

    # Heuristische aanvulling drinkvenster als enrichment het niet gaf
    win_from = data.get("window_from") or (data.get("drinking_window") or {}).get("from")
    win_to = data.get("window_to") or (data.get("drinking_window") or {}).get("to")
    if not win_from or not win_to:
        frm, to = _heuristic_window(color=color, grapes=grapes, climate=climate, vintage=vintage)
        if frm and to:
            data["window_from"] = frm
            data["window_to"] = to
            # optioneel ook in notes opnemen voor zichtbaarheid:
            notes = data.get("notes") or ""
            hint = f"Sugg. drinkvenster: {frm}–{to}."
            data["notes"] = (notes + ("\n\n" if notes else "") + hint).strip()

    return data

# ---------- Admin: opslaan nieuwe wijn ----------
@app.post("/api/admin/wine")
def admin_save_wine(payload: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """
    Sla wijn + (gefinetunede) profiel + optionele notities op.
    Vereist velden: name, region, climate, grapes, vintage, profile
    """
    required = ["name", "region", "climate", "grapes", "vintage", "profile"]
    for f in required:
        if f not in payload:
            raise HTTPException(400, f"Ontbrekend veld: {f}")

    prof = dict(payload["profile"] or {})
    for k in ["ZB", "MG", "LS", "PA", "GF"]:
        v = int(prof.get(k, 50))
        prof[k] = max(0, min(100, v))

    # Altijd aanwezige kolommen
    w = Wine(
        name=payload["name"],
        region=payload["region"],
        climate=payload["climate"],
        grapes=payload["grapes"],
        vintage=int(payload["vintage"]),
        soil=payload.get("soil"),
        oak_months=int(payload.get("oak_months") or 0),
        abv=payload.get("abv"),
        price_eur=payload.get("price_eur"),  # blijft ondersteund indien aanwezig
        profile=prof,
        confidence=0.9,
        notes=payload.get("notes"),
        sources=payload.get("sources"),
        bottles=int(payload.get("bottles") or 1),
    )

    # Optionele/nieuwe kolommen alleen zetten als ze bestaan in het model
    for opt_key in [
        "producer", "color", "sweetness",
        "purchase_price_eur", "bottle_size_ml", "storage_location",
        "elevage", "food_pairings",
        "drinking_from", "drinking_to",
    ]:
        if hasattr(w, opt_key) and opt_key in payload:
            setattr(w, opt_key, payload.get(opt_key))

    db.add(w); db.commit(); db.refresh(w)
    return {"id": w.id}

# ---------- Admin: voorraadlijst + bewerken/verwijderen ----------
class WineUpdate(BaseModel):
    # basis
    name: Optional[str] = None
    producer: Optional[str] = None
    region: Optional[str] = None
    vintage: Optional[int] = None
    climate: Optional[str] = None
    soil: Optional[str] = None
    elevage: Optional[str] = None
    abv: Optional[float] = None
    grapes: Optional[list] = None  # [{"variety":..., "weight":...}]
    # meta
    color: Optional[str] = None
    sweetness: Optional[str] = None
    # prijzen & flessen
    price_eur: Optional[float] = None
    purchase_price_eur: Optional[float] = None
    bottle_size_ml: Optional[int] = None
    bottles: Optional[int] = None
    storage_location: Optional[str] = None
    # drinkvenster
    drinking_from: Optional[int] = None
    drinking_to: Optional[int] = None
    # extra
    food_pairings: Optional[str] = None
    profile: Optional[dict] = None
    notes: Optional[str] = None
    sources: Optional[List[dict]] = None

@app.get("/api/admin/wines")
def admin_list_wines(
    q: str = Query("", description="Zoekterm op naam/region/grape"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    rows = db.query(Wine).all()
    # Voor zoeken ook druiven meenemen
    def grapes_join(w: Wine) -> str:
        try:
            if w.grapes and isinstance(w.grapes, list):
                return ", ".join([g.get("variety") or "" for g in w.grapes if g.get("variety")])
        except Exception:
            pass
        return ""

    ql = (q or "").strip().lower()
    if ql:
        out = []
        for w in rows:
            gj = grapes_join(w).lower()
            if ql in (w.name or "").lower() or ql in (w.region or "").lower() or ql in gj:
                out.append(w)
        rows = out

    total = len(rows)
    page = rows[offset:offset+limit]
    items = []
    for w in page:
        gj = grapes_join(w)
        items.append({
            "id": w.id,
            "name": w.name,
            "region": w.region,
            "vintage": w.vintage,
            "bottles": getattr(w, "bottles", None),
            "climate": w.climate,
            "grapes": w.grapes,           # voor client tonen
            "grapes_join": gj,            # voor client-side zoeken/tonen
        })
    return {"total": total, "items": items}

# Volledige wijn ophalen
@app.get("/api/admin/wine/{wine_id}")
def admin_get_wine(wine_id: int, db: Session = Depends(get_db)):
    w = db.get(Wine, wine_id)
    if not w:
        raise HTTPException(404, "Wine not found")
    return {
        "id": w.id,
        "name": w.name,
        "producer": getattr(w, "producer", None),
        "region": w.region,
        "climate": w.climate,
        "grapes": w.grapes,
        "vintage": w.vintage,
        "soil": w.soil,
        "oak_months": w.oak_months,
        "elevage": getattr(w, "elevage", None),
        "abv": w.abv,
        "color": getattr(w, "color", None),
        "sweetness": getattr(w, "sweetness", None),
        "price_eur": getattr(w, "price_eur", None),
        "purchase_price_eur": getattr(w, "purchase_price_eur", None),
        "bottles": getattr(w, "bottles", None),
        "bottle_size_ml": getattr(w, "bottle_size_ml", None),
        "storage_location": getattr(w, "storage_location", None),
        "drinking_from": getattr(w, "drinking_from", None),
        "drinking_to": getattr(w, "drinking_to", None),
        "food_pairings": getattr(w, "food_pairings", None),
        "profile": w.profile,
        "confidence": w.confidence,
        "notes": w.notes,
        "sources": w.sources,
    }

@app.patch("/api/admin/wine/{wine_id}")
def admin_update_wine(wine_id: int, body: WineUpdate, db: Session = Depends(get_db)):
    w = db.get(Wine, wine_id)
    if not w:
        raise HTTPException(404, "Wine not found")

    data = body.dict(exclude_unset=True)

    # clamp sliders indien aanwezig
    if "profile" in data and data["profile"] is not None:
        for k in ["ZB", "MG", "LS", "PA", "GF"]:
            if k in data["profile"] and data["profile"][k] is not None:
                v = int(data["profile"][k])
                data["profile"][k] = max(0, min(100, v))

    # Alleen kolommen zetten die bestaan op het model
    for k, v in list(data.items()):
        if hasattr(w, k):
            setattr(w, k, v)
        # zo niet: negeren (forward compatible)

    db.commit(); db.refresh(w)
    return {"ok": True}

@app.delete("/api/admin/wine/{wine_id}")
def admin_delete_wine(wine_id: int, db: Session = Depends(get_db)):
    w = db.get(Wine, wine_id)
    if not w:
        raise HTTPException(404, "Wine not found")
    db.delete(w); db.commit()
    return {"ok": True}
