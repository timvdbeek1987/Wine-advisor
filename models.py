# models.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# 5 assen van zowel user als wine-profielen
AxisNames = ["ZB", "MG", "LS", "PA", "GF"]  # Zintuiglijk, Mondgevoel, Levensstijl, Pers. Associatie, Gelegenheid

class WineIn(BaseModel):
    name: str
    region: str
    climate: str  # "cool" | "moderate" | "warm"
    grapes: List[Dict[str, float]]  # [{"variety": "Chenin Blanc", "weight": 1.0}]
    vintage: int
    soil: Optional[str] = None      # "granite"|"schist"|"limestone"|"clay"|"sand"|"volcanic"|None
    oak_months: int = 0
    abv: Optional[float] = None
    price_eur: Optional[float] = None

class WineDB(WineIn):
    id: int
    profile: Dict[str, float]
    confidence: float

class UserAnswer(BaseModel):
    question_id: str
    option_id: str

class UserQuizResult(BaseModel):
    profile: Dict[str, float]      # 5D vector 0..100
    budget_band: Optional[str] = None
    tannin_pref: Optional[str] = None  # "low"|"medium"|"high"|None

class MatchRequest(BaseModel):
    quiz_answers: List[UserAnswer]

class MatchResult(BaseModel):
    wine: WineDB
    similarity: float
    why: str