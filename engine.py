# engine.py
from __future__ import annotations
from typing import Dict, List, Tuple
import math
import numpy as np

AXES = ["ZB", "MG", "LS", "PA", "GF"]

# ---- 1) Prototypes per druif (basisprofiel) ----
GRAPE_PROTOTYPES: Dict[str, Dict[str, float]] = {
    "Sauvignon Blanc": {"ZB":78, "MG":32, "LS":48, "PA":72, "GF":48},
    "Chardonnay":      {"ZB":60, "MG":46, "LS":52, "PA":56, "GF":54},  # unoaked baseline
    "Riesling":        {"ZB":84, "MG":30, "LS":58, "PA":70, "GF":46},
    "Chenin Blanc":    {"ZB":72, "MG":42, "LS":54, "PA":66, "GF":52},
    "Pinot Noir":      {"ZB":64, "MG":40, "LS":60, "PA":58, "GF":58},
    "Grenache":        {"ZB":52, "MG":62, "LS":54, "PA":50, "GF":62},
    "Merlot":          {"ZB":50, "MG":66, "LS":50, "PA":46, "GF":66},
    "Syrah":           {"ZB":46, "MG":74, "LS":58, "PA":44, "GF":74},
    "Cabernet Sauvignon":{"ZB":44, "MG":82, "LS":56, "PA":42, "GF":82},
}

# ---- 2) Correcties ----
def climate_adjust(climate: str) -> Dict[str, int]:
    if climate == "cool":
        return {"ZB": +8, "MG": -6, "PA": +6, "GF": -2}
    if climate == "warm":
        return {"ZB": -8, "MG": +8, "PA": -4, "GF": +4}
    return {"ZB": 0, "MG": 0, "PA": 0, "GF": 0}  # moderate

def soil_adjust(soil: str|None) -> Dict[str, int]:
    m = {"ZB":0,"MG":0,"LS":0,"PA":0,"GF":0}
    if not soil: return m
    if soil == "granite":
        m["ZB"] += 4; m["PA"] += 4
    elif soil in ("schist","slate","schist/slate"):
        m["GF"] += 4; m["PA"] -= 2
    elif soil == "limestone":
        m["ZB"] += 6
    elif soil == "clay":
        m["MG"] += 6; m["GF"] += 2
    elif soil == "sand":
        m["MG"] -= 4; m["LS"] += 2
    elif soil == "volcanic":
        m["LS"] += 8; m["PA"] += 2; m["GF"] += 2
    return m

def oak_adjust(oak_months: int) -> Dict[str, int]:
    m = {"ZB":0,"MG":0,"LS":0,"PA":0,"GF":0}
    if oak_months <= 0:
        m["ZB"] += 4; m["MG"] -= 4; m["LS"] += 2
    elif 3 <= oak_months <= 8:
        m["MG"] += 4; m["GF"] += 2
    elif 9 <= oak_months <= 18:
        m["MG"] += 8; m["GF"] += 6; m["ZB"] -= 4; m["PA"] -= 2
    elif oak_months > 18:
        m["MG"] += 12; m["GF"] += 8; m["ZB"] -= 8; m["PA"] -= 4
    return m

def vintage_adjust(vintage_vs_norm: str) -> Dict[str, int]:
    if vintage_vs_norm == "cooler":
        return {"ZB": +4, "MG": -2}
    if vintage_vs_norm == "warmer":
        return {"ZB": -4, "MG": +2, "GF": +2}
    return {"ZB":0,"MG":0,"GF":0}

def clamp01(v: float) -> float:
    return max(0.0, min(100.0, v))

def sum_profiles(a: Dict[str, float], b: Dict[str, float]) -> Dict[str, float]:
    return {k: a.get(k,0) + b.get(k,0) for k in AXES}

# ---- 3) Wine profile builder ----
def build_wine_profile(*, grapes: list[dict], climate: str, soil: str|None, oak_months: int, vintage_vs_norm: str|None) -> tuple[dict, float]:
    # 1) start: gewogen gemiddelde van druifprototypes
    P = {k:0.0 for k in AXES}
    total_w = 0.0
    for g in grapes:
        variety = g["variety"]
        weight = float(g.get("weight", 0))
        proto = GRAPE_PROTOTYPES.get(variety)
        if not proto:
            continue
        for k in AXES:
            P[k] += proto[k] * weight
        total_w += weight
    if total_w > 0:
        P = {k: P[k]/total_w for k in AXES}
    else:
        # onbekende druif? neutraal
        P = {"ZB":50,"MG":50,"LS":50,"PA":50,"GF":50}

    # 2) correcties
    c1 = climate_adjust(climate)
    c2 = soil_adjust(soil)
    c3 = oak_adjust(oak_months)
    c4 = vintage_adjust(vintage_vs_norm or "normal")

    for m in (c1,c2,c3,c4):
        for k,v in m.items():
            P[k] = P.get(k,50) + v

    # 3) clamp & confidence
    P = {k: clamp01(v) for k,v in P.items()}
    known_bits = 0
    known_bits += 1 if total_w > 0 else 0
    known_bits += 1 if climate else 0
    known_bits += 1 if soil else 0
    known_bits += 1 if oak_months is not None else 0
    known_bits += 1 if vintage_vs_norm is not None else 0
    confidence = min(1.0, 0.15 + 0.17*known_bits)  # simpele schatting (0.15..1.0)

    return P, confidence

# ---- 4) Quiz scoring ----
# Start op 50, elk antwoord geeft delta's
QUIZ_DELTAS: dict[str, dict[str, dict[str,int]]] = {
    # question_id: { option_id: {axis: delta, ...} }
    "Q1": {
        "A": {"ZB":+8,"MG":-4}, "B":{"ZB":+4,"MG":-2},
        "C":{"ZB":-6,"MG":+8}, "D":{"ZB":-2,"MG":+6},
    },
    "Q2": {
        "A":{"PA":+10,"ZB":+6},
        "B":{"PA":-10,"MG":+6},
        "C":{"LS":+8,"GF":+4},
        "D":{"GF":+10,"MG":+4},
    },
    "Q3": {
        "A":{"ZB":+10,"GF":+6},
        "B":{"MG":+8,"PA":-4},
        "C":{"ZB":+6,"LS":+2},
        "D":{"MG":+6,"GF":+4},
    },
    "Q4": {
        "A":{"ZB":+10,"MG":-4},
        "B":{"MG":+10,"ZB":-6},
        "C":{"MG":+6,"LS":+6},
        "D":{"ZB":+6,"LS":+4},
    },
    "Q5": {
        "A":{"LS":-10,"GF":+6},
        "B":{"ZB":+8,"PA":+6},
        "C":{"MG":+8,"ZB":-4},
        "D":{"LS":+12,"MG":+2},
    },
    "Q6": {
        "A":{"ZB":+10}, "B":{"MG":+8}, "C":{"MG":+6,"LS":+2}, "D":{"GF":+8,"PA":-4},
    },
    "Q7": {
        "A":{"ZB":+10,"GF":+8},
        "B":{"MG":+10,"GF":+8},
        "C":{"LS":+8,"ZB":+2},
        "D":{"PA":+6,"GF":-6},
    },
    "Q8": {
        "A":{"LS":-12}, "B":{"LS":+12}, "C":{"LS":0,"GF":+2},
    },
    "Q9": {
        "A":{"MG":+4,"ZB":+2},
        "B":{"MG":+8},
        "C":{"MG":+12,"ZB":-4},
        "D":{"ZB":+4},
    },
    "Q10":{
        "A":{"GF":-2}, "B":{"GF":+2}, "C":{"GF":+8}, "D":{"GF":+12,"LS":+4},
    }
}

def build_user_profile(answers: list[dict]) -> dict:
    P = {k:50.0 for k in AXES}
    for ans in answers:
        deltas = QUIZ_DELTAS.get(ans["question_id"],{}).get(ans["option_id"],{})
        for k,v in deltas.items():
            P[k] = clamp01(P[k] + v)
    return P

# ---- 5) Similarity (gewogen cosine) ----
WEIGHTS = np.array([0.30, 0.30, 0.20, 0.12, 0.08], dtype=float)  # ZB, MG, GF, LS, PA
AXIS_ORDER = ["ZB","MG","GF","LS","PA"]

def weighted_cosine(a: dict, b: dict) -> float:
    va = np.array([a[x] for x in AXIS_ORDER], dtype=float)
    vb = np.array([b[x] for x in AXIS_ORDER], dtype=float)
    w = WEIGHTS
    va = va * w
    vb = vb * w
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)

def explain_match(user: dict, wine: dict) -> str:
    msgs = []
    # kies 2 sterkste assen van user
    strongest = sorted(user.items(), key=lambda kv: kv[1], reverse=True)[:2]
    for axis, val in strongest:
        if axis == "ZB":
            msgs.append("je scoort hoog op **frisheid**; deze wijn sluit daar mooi op aan")
        elif axis == "MG":
            msgs.append("je houdt van een bepaald **mondgevoel**; dit profiel matcht in structuur")
        elif axis == "GF":
            msgs.append("je zoekt **eet-matches**; deze wijn doet het goed aan tafel")
        elif axis == "LS":
            msgs.append("je stijl is **klassiek/avontuurlijk**; dit past bij de wijnkeuze")
        elif axis == "PA":
            msgs.append("je associeert met **sfeer**; deze wijn raakt die toon")
    return " & ".join(msgs) or "goede algehele match met jouw profiel"