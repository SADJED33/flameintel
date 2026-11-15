"""Paths, scenarios and the ranking weights (all in one place, on purpose)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # project root (contains chat.py)
API_DIR = Path(__file__).resolve().parent
DATA_DIR = API_DIR / "data"                             # generated JSON (investigations, insights)
RAW_DIR = ROOT / "raw"                                  # real NASA files
KB_DATA = ROOT / "data"                                 # experiments.json, known_gaps.txt, coverage.csv
BUILD_DIR = ROOT / "build"                              # runs.jsonl, index_skipped.csv, ...

CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
RATE_LIMIT_PER_MIN = 12          # /api/chat requests per IP per minute

SCENARIOS = ["Spacecraft", "ISS", "Lunar Habitat", "Mars Habitat", "Pressurized Rover"]

# ---------------------------------------------------------------------------------------------
# Relevance heuristic. NOT an official NASA score: an app-generated aid to decide what to read first.
# score = 100 * sum(weight_i * component_i), each component in [0, 1].
# ---------------------------------------------------------------------------------------------
RANK_WEIGHTS = {
    "topic": 0.40,        # topic alignment (scenario topics + the user's search words)
    "environment": 0.20,  # experiment platform vs. chosen scenario
    "data": 0.20,         # accessible tabular data files / indexed table rows
    "coverage": 0.20,     # source coverage: indexed chunks, document types, publications
}

# topics each scenario cares about, with a weight in [0, 1] (heuristic, editable)
SCENARIO_TOPICS = {
    "Spacecraft":        {"flame spread": 1.0, "flammability": 1.0, "smoke & detection": 0.9, "suppression & extinguishment": 0.9, "combustion behavior": 0.5},
    "ISS":               {"flame spread": 0.9, "smoke & detection": 1.0, "suppression & extinguishment": 1.0, "flammability": 0.8, "combustion behavior": 0.6},
    "Lunar Habitat":     {"flame spread": 1.0, "flammability": 1.0, "suppression & extinguishment": 0.8, "smoke & detection": 0.7, "combustion behavior": 0.5},
    "Mars Habitat":      {"flame spread": 1.0, "flammability": 1.0, "suppression & extinguishment": 0.8, "smoke & detection": 0.7, "combustion behavior": 0.5},
    "Pressurized Rover": {"smoke & detection": 1.0, "flammability": 0.9, "suppression & extinguishment": 0.9, "flame spread": 0.8, "combustion behavior": 0.4},
}

# platform alignment per scenario (heuristic): environment tag -> component value
SCENARIO_ENV = {
    "Spacecraft":        {"Spacecraft (Cygnus)": 1.0, "ISS": 0.8, "Ground / modeling": 0.4},
    "ISS":               {"ISS": 1.0, "Spacecraft (Cygnus)": 0.8, "Ground / modeling": 0.4},
    "Lunar Habitat":     {"ISS": 0.5, "Spacecraft (Cygnus)": 0.5, "Ground / modeling": 0.4},
    "Mars Habitat":      {"ISS": 0.5, "Spacecraft (Cygnus)": 0.5, "Ground / modeling": 0.4},
    "Pressurized Rover": {"ISS": 0.5, "Spacecraft (Cygnus)": 0.5, "Ground / modeling": 0.4},
}

GRAVITY_NOTE = {
    "Spacecraft":        "Spacecraft are in microgravity; check that the test conditions match the vehicle's atmosphere.",
    "ISS":               "Matches the ISS microgravity condition; cabin atmosphere and airflow may still differ from the test.",
    "Lunar Habitat":     "Lunar gravity is about 1/6 g. Flight experiments here were run in microgravity, not lunar gravity.",
    "Mars Habitat":      "Mars gravity is about 3/8 g. Flight experiments here were run in microgravity, not Mars gravity.",
    "Pressurized Rover": "A rover operates under partial gravity or on Earth. Flight experiments here were run in microgravity.",
}

# keyword rules that tag topics from the SOURCE text (title/objective/approach/hypothesis/description)
TOPIC_RULES = {
    "flame spread":                 ["flame spread", "flame-spread", "spread rate", "concurrent", "opposed flow", "opposed-flow"],
    "flammability":                 ["flammab", "ignition", "limiting oxygen", "burn time", "material flammab", "fire safety", "fire-safety"],
    "suppression & extinguishment": ["suppress", "extinguish", "quench", "water mist", "fire fighting", "fire-fighting"],
    "smoke & detection":            ["smoke", "aerosol", "detector"],
    "cool flames":                  ["cool flame", "cool-flame", "low-temperature", "low temperature"],
    "soot & smoke point":           ["soot", "smoke point"],
    "diffusion flames":             ["diffusion flame", "laminar", "co-flow", "coflow", "spherical flame", "liftoff"],
    "combustion behavior":          ["combustion", "flame", "burning"],
    "modeling & simulation":        ["modeling", "modelling", "simulation", "cfd", "numerical", "computational"],
}

# anything that matches these is excluded from the app (hard rule: no rocket/propellant research)
EXCLUDE_TERMS = ["propellant", "rocket engine", "rocket motor", "launch vehicle"]

# optional word-boundary issue: acronyms that should not be tagged by substring

# Curated, clearly-labelled "potential application" text per topic. These are FlameIntel's own wording,
# NOT statements from NASA sources, and every one requires validation.
POTENTIAL_APPLICATIONS = {
    "flame spread": "May inform future screening tests of how fire spreads over materials in enclosed habitats.",
    "flammability": "May inform future evaluation of fire-resistant materials for enclosed habitats. It does not certify any material for spacecraft use.",
    "suppression & extinguishment": "May inform future research on fire-suppression approaches (Earth analogues include fine water-mist systems), once tested at relevant gravity and atmosphere.",
    "smoke & detection": "May inform future evaluation of smoke and fire detectors, since smoke behaves differently in microgravity.",
    "cool flames": "May inform low-temperature combustion research relevant to fuels and ignition hazards.",
    "soot & smoke point": "May inform understanding of smoke and soot production, relevant to detection and crew air-quality research.",
    "diffusion flames": "May inform basic flame models that feed fire-safety simulations.",
    "modeling & simulation": "May help calibrate fire-safety simulation tools, after validation against the real experiments.",
    "combustion behavior": "Background combustion science that fire-safety research can build on.",
}
