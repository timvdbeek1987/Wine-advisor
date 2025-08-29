# db.py
from sqlalchemy import create_engine, Column, Integer, String, Float, JSON, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

# --- SQLite pad als absoluut pad ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "wine.db")
DB_URL = f"sqlite:///{DB_PATH}"

# --- SQLAlchemy setup ---
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# --- Model ---
class Wine(Base):
    __tablename__ = "wines"
    id = Column(Integer, primary_key=True, index=True)

    # Basis
    name = Column(String, nullable=False)
    producer = Column(String, nullable=True)              # huis/domein
    country = Column(String, nullable=True)               # NIEUW: land
    region = Column(String, nullable=False)
    climate = Column(String, nullable=False)              # "cool" | "temperate" | "warm"
    color = Column(String, nullable=True)                 # NIEUW: "red" | "white" | "rosé" | "sparkling"
    sweetness = Column(String, nullable=True)             # NIEUW: "dry" | "off-dry" | ...

    # Samenstelling & stijl
    grapes = Column(JSON, nullable=False)                 # [{"variety": str, "weight": float}, ...]
    vintage = Column(Integer, nullable=False)
    soil = Column(String, nullable=True)
    oak_months = Column(Integer, default=0)
    elevage = Column(String, nullable=True)               # "oak, stainless, amphora", etc.
    abv = Column(Float, nullable=True)

    # Prijzen & voorraad
    price_eur = Column(Float, nullable=True)              # optioneel (legacy)
    purchase_price_eur = Column(Float, nullable=True)     # inkoopprijs
    bottle_size_ml = Column(Integer, default=750)         # flesgrootte (ml)
    bottles = Column(Integer, default=1)                  # voorraad-aantal
    storage_location = Column(String, nullable=True)      # locatie in kelder/rek

    # Drinkvenster & pairings
    drinking_from = Column(Integer, nullable=True)        # jaar vanaf
    drinking_to = Column(Integer, nullable=True)          # jaar t/m
    food_pairings = Column(Text, nullable=True)           # vrije tekst of JSON-string

    # Profiel & meta
    profile = Column(JSON, nullable=False)                # {"ZB":int,"MG":int,"LS":int,"PA":int,"GF":int}
    confidence = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)

# --- Init + mini-migratie ---
def init_db():
    # Maak tabellen aan als ze niet bestaan
    Base.metadata.create_all(bind=engine)

    # Lichte migraties voor bestaande DB's: voeg kolommen toe als ze nog ontbreken
    with engine.connect() as conn:
        cols = {c[1] for c in conn.execute(text("PRAGMA table_info(wines)")).fetchall()}

        def add(col_sql: str):
            conn.execute(text(col_sql))

        if "bottles" not in cols:
            add("ALTER TABLE wines ADD COLUMN bottles INTEGER DEFAULT 1")
        if "producer" not in cols:
            add("ALTER TABLE wines ADD COLUMN producer TEXT")
        if "country" not in cols:
            add("ALTER TABLE wines ADD COLUMN country TEXT")
        if "elevage" not in cols:
            add("ALTER TABLE wines ADD COLUMN elevage TEXT")
        if "purchase_price_eur" not in cols:
            add("ALTER TABLE wines ADD COLUMN purchase_price_eur REAL")
        if "bottle_size_ml" not in cols:
            add("ALTER TABLE wines ADD COLUMN bottle_size_ml INTEGER DEFAULT 750")
        if "storage_location" not in cols:
            add("ALTER TABLE wines ADD COLUMN storage_location TEXT")
        if "drinking_from" not in cols:
            add("ALTER TABLE wines ADD COLUMN drinking_from INTEGER")
        if "drinking_to" not in cols:
            add("ALTER TABLE wines ADD COLUMN drinking_to INTEGER")
        if "food_pairings" not in cols:
            add("ALTER TABLE wines ADD COLUMN food_pairings TEXT")
        if "color" not in cols:
            add("ALTER TABLE wines ADD COLUMN color TEXT")
        if "sweetness" not in cols:
            add("ALTER TABLE wines ADD COLUMN sweetness TEXT")

        conn.commit()

# --- Session dependency voor FastAPI ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
