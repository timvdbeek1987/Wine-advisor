# enrichment.py
from __future__ import annotations
import re, html
from typing import Dict, List, Tuple, Optional
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "WineAdvisor/0.2 (+demo)"}

# --- Lexicon → as-delta’s ---
LEXICON = [
    (r"\b(citrus|citroen|lemon|lime|grapefruit|green apple|mineral|minera(a|)l|saline|zilt)\b", {"ZB": +8}),
    (r"\b(crisp|knisperend|fris|strak|steely|zesty)\b", {"ZB": +6}),
    (r"\b(oak|barrique|vanilla|boterig|buttery|toast|rook|smoke)\b", {"MG": +8, "ZB": -4, "GF": +4}),
    (r"\b(cream|romig|malo|malolactic)\b", {"MG": +6, "ZB": -2}),
    (r"\b(tannin|tannine|firm|grip|structured)\b", {"MG": +8, "GF": +4}),
    (r"\b(pepper|peper|spice|kruidig)\b", {"LS": +4, "MG": +2}),
    (r"\b(tropical|tropisch|mango|pineapple|ananas|guava)\b", {"MG": +4, "ZB": -2}),
    (r"\b(berries|bessen|cherry|kers)\b", {"MG": +2}),
    (r"\b(acid|acidity|zuur|hoge zuurgraad)\b", {"ZB": +6}),
    (r"\b(full[- ]?bodied|full|vol|krachtig)\b", {"MG": +8, "GF": +4}),
    (r"\b(light|licht|elegant|fijn)\b", {"MG": -6, "ZB": +2}),
    (r"\b(food pair|pairing|bij eten|gastronom)\b", {"GF": +6}),
]

def clamp_delta(d: Dict[str,int]) -> Dict[str,int]:
    out = {"ZB":0,"MG":0,"LS":0,"PA":0,"GF":0}
    for k,v in d.items():
        out[k] = max(-12, min(12, int(v)))
    return out

# --- Wikipedia summary via REST API (documentatie: Wikimedia REST) ---
# ref: https://api.wikimedia.org/ (REST API), en page summary endpoints.  [oai_citation:0‡wikimedia.org](https://wikimedia.org/api/rest_v1/?utm_source=chatgpt.com) [oai_citation:1‡api.wikimedia.org](https://api.wikimedia.org/wiki/Core_REST_API/Reference/Pages/Get_page?utm_source=chatgpt.com)
def wiki_summary(term: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        slug = term.strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
        r = requests.get(url, timeout=6, headers=HEADERS)
        if r.status_code == 200:
            data = r.json()
            title = data.get("title")
            extract = data.get("extract")
            pageurl = data.get("content_urls",{}).get("desktop",{}).get("page") or f"https://en.wikipedia.org/wiki/{slug}"
            return title, extract, pageurl
    except Exception:
        pass
    return None, None, None

def score_text_to_axes(text: str) -> Dict[str, int]:
    text_low = text.lower()
    acc: Dict[str, int] = {"ZB":0,"MG":0,"LS":0,"PA":0,"GF":0}
    for pat, delta in LEXICON:
        if re.search(pat, text_low):
            for k,v in delta.items():
                acc[k] = acc[k] + v
    return clamp_delta(acc)

# --- Publieke vintage bronnen (link-only best effort) ---
# Wine Enthusiast vintage chart (publieke bron, jaarlijkse update).  [oai_citation:2‡Wine Enthusiast](https://www.wineenthusiast.com/wine-vintage-chart/?srsltid=AfmBOoqLBlrau0Pae2iMCw8BgrHm9rRlZ9t-fVvUa_CskxUr0rpnrP9N&utm_source=chatgpt.com)
WE_VINTAGE_URL = "https://www.wineenthusiast.com/wine-vintage-chart/"

# Wine-Searcher vintage chart (publieke overzichtspagina per regio/jaar).  [oai_citation:3‡Wine-Searcher](https://www.wine-searcher.com/vintage-chart?srsltid=AfmBOoqeG9ONSbjnVz299XJ2eEmU5yVHaV64FMceBzKS3UX2duJcIaKM&utm_source=chatgpt.com)
WS_VINTAGE_URL = "https://www.wine-searcher.com/vintage-chart"

def fetch_vintage_hint(country: Optional[str], region: Optional[str], vintage: Optional[int]) -> Dict[str,str]:
    """
    We scrapen niet agressief; we geven vooral bruikbare links terug voor context.
    Heuristisch tekstje voor UI + bronverwijzing.
    """
    hint = {}
    terms = []
    if country: terms.append(country)
    if region: terms.append(region)
    if vintage: terms.append(str(vintage))
    q = " ".join(terms) if terms else ""

    # Maak compacte boodschap met anker naar bronnen
    links = []
    if q:
        links.append({"label":"Wine Enthusiast vintage chart", "url": WE_VINTAGE_URL})
        links.append({"label":"Wine-Searcher vintage chart", "url": WS_VINTAGE_URL})
    if links:
        hint["vintage_note"] = f"Check vintage-indicatie voor '{q}' bij onderstaande bronnen (gemiddelde kwaliteit & drinkvenster)."
        hint["vintage_links"] = links
    return hint

def enrich_wine(grape_terms: List[str], region_term: Optional[str], country: Optional[str]=None, vintage: Optional[int]=None) -> Dict:
    notes = []
    sources = []

    # 1) Wikipedia: druiven + regio
    for g in grape_terms:
        t, extract, link = wiki_summary(g)
        if extract:
            notes.append(f"[{t}] {extract}")
            sources.append({"type":"wikipedia","term":g,"url":link})
    if region_term:
        t, extract, link = wiki_summary(region_term)
        if extract:
            notes.append(f"[{t}] {extract}")
            sources.append({"type":"wikipedia","term":region_term,"url":link})

    combined = " ".join(notes)
    axes_delta = score_text_to_axes(combined) if combined else {"ZB":0,"MG":0,"LS":0,"PA":0,"GF":0}

    # 2) Vintage-hint (links naar overzichtstabellen i.p.v. zware scraping)
    vint = fetch_vintage_hint(country, region_term, vintage)
    if vint.get("vintage_note"):
        notes.append(vint["vintage_note"])
        for lk in vint.get("vintage_links", []):
            sources.append({"type":"vintage", "term": lk["label"], "url": lk["url"]})

    # Limit tekstlengte voor UI
    summary = "\n\n".join(notes[:5])
    return {"notes": summary, "axes_delta": axes_delta, "sources": sources}