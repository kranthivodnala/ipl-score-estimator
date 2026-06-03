from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import mlflow
import mlflow.xgboost
import mlflow.lightgbm
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
import os
import time
import threading

# ── MLflow setup ───────────────────────────────────────────────────────────
MLFLOW_URI   = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MODEL_STAGE  = os.getenv("MODEL_STAGE", "Production")  # Production or Staging
mlflow.set_tracking_uri(MLFLOW_URI)

# ── Global model store ─────────────────────────────────────────────────────
models = {}
models_ready = False
MODEL_NAME   = "ipl-score-predictor"

def load_models_background():
    global models_ready

    MODEL_PATH = os.getenv("MODEL_PATH", None)

    try:
        print(f"\n🏏 Loading model stage='{MODEL_STAGE}'...")
        t0 = time.time()

        if MODEL_PATH:
            # Load directly from mounted path — no MLflow registry needed
            print(f"   Loading from local path: {MODEL_PATH}")
            if MODEL_STAGE == "Production":
                models["a"] = mlflow.xgboost.load_model(MODEL_PATH)
                models["b"] = None
            else:
                models["a"] = None
                models["b"] = mlflow.lightgbm.load_model(MODEL_PATH)
        else:
            # Fallback to registry
            alias = "Production" if MODEL_STAGE == "Production" else "Staging"
            model_uri = f"models:/{MODEL_NAME}@{alias}"
            if MODEL_STAGE == "Production":
                models["a"] = mlflow.xgboost.load_model(model_uri)
                models["b"] = None
            else:
                models["a"] = None
                models["b"] = mlflow.lightgbm.load_model(model_uri)

        models_ready = True
        print(f"   ✅ Model '{MODEL_STAGE}' ready in {time.time()-t0:.1f}s\n")

    except Exception as e:
        print(f"   ❌ Model loading failed: {e}")

# ── Lifespan ───────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fire model loading in background thread — FastAPI starts immediately
    thread = threading.Thread(target=load_models_background, daemon=True)
    thread.start()
    print("🏏 IPL Score Predictor started — models loading in background...")
    yield
    print("🏏 Shutting down...")
    models.clear()

# ── App ────────────────────────────────────────────────────────────────────
app = FastAPI(title="IPL Score Predictor", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Encoders ───────────────────────────────────────────────────────────────
ALL_TEAMS = [
    'Chennai Super Kings', 'Deccan Chargers', 'Delhi Capitals',
    'Delhi Daredevils', 'Gujarat Lions', 'Gujarat Titans',
    'Kings XI Punjab', 'Kochi Tuskers Kerala', 'Kolkata Knight Riders',
    'Lucknow Super Giants', 'Mumbai Indians', 'Pune Warriors',
    'Punjab Kings', 'Rajasthan Royals', 'Rising Pune Supergiant',
    'Rising Pune Supergiants', 'Royal Challengers Bangalore',
    'Royal Challengers Bengaluru', 'Sunrisers Hyderabad'
]

ALL_VENUES = [
    'M Chinnaswamy Stadium',
    'Punjab Cricket Association Stadium, Mohali',
    'Feroz Shah Kotla', 'Wankhede Stadium', 'Eden Gardens',
    'Sawai Mansingh Stadium',
    'Rajiv Gandhi International Cricket Stadium',
    'MA Chidambaram Stadium', 'Dr DY Patil Sports Academy',
    'Newlands', 'St Georges Park', 'Kingsmead', 'SuperSport Park',
    'Buffalo Park', 'New Wanderers Stadium', 'De Beers Diamond Oval',
    'OUTsurance Oval', 'Brabourne Stadium',
    'Maharashtra Cricket Association Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Mohali',
    'Saurashtra Cricket Association Stadium',
    'Sharjah Cricket Stadium',
    'Dubai International Cricket Stadium', 'Sheikh Zayed Stadium',
    'Arun Jaitley Stadium',
    'Dr. Y.S. Rajasekhara Reddy ACA-VDCA Cricket Stadium',
    'Holkar Cricket Stadium',
    'Mumbai Cricket Association Ground',
    'Narendra Modi Stadium, Ahmedabad',
    'JSCA International Stadium Complex',
    'Barsapara Cricket Stadium',
    'Himachal Pradesh Cricket Association Stadium',
    'Ekana Cricket Stadium',
    'Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium'
]

CURRENT_TEAMS = [
    'Chennai Super Kings', 'Delhi Capitals', 'Gujarat Titans',
    'Kolkata Knight Riders', 'Lucknow Super Giants', 'Mumbai Indians',
    'Punjab Kings', 'Rajasthan Royals', 'Royal Challengers Bengaluru',
    'Sunrisers Hyderabad',
]

CURRENT_VENUES = [
    'Wankhede Stadium',
    'MA Chidambaram Stadium',
    'Eden Gardens',
    'M Chinnaswamy Stadium',
    'Arun Jaitley Stadium',
    'Narendra Modi Stadium, Ahmedabad',
    'Rajiv Gandhi International Cricket Stadium',
    'Sawai Mansingh Stadium',
    'Punjab Cricket Association IS Bindra Stadium, Mohali',
    'Ekana Cricket Stadium',
]

le_team  = LabelEncoder().fit(ALL_TEAMS)
le_venue = LabelEncoder().fit(ALL_VENUES)

# ── Static lookup tables ───────────────────────────────────────────────────
VENUE_AVG = {
    'Wankhede Stadium': 172,
    'MA Chidambaram Stadium': 155,
    'Eden Gardens': 163,
    'M Chinnaswamy Stadium': 170,
    'Arun Jaitley Stadium': 160,
    'Narendra Modi Stadium, Ahmedabad': 168,
    'Rajiv Gandhi International Cricket Stadium': 165,
    'Sawai Mansingh Stadium': 158,
    'Punjab Cricket Association IS Bindra Stadium, Mohali': 162,
    'Ekana Cricket Stadium': 161,
}

TEAM_AVG = {
    'Chennai Super Kings': 166, 'Delhi Capitals': 161,
    'Gujarat Titans': 163,      'Kolkata Knight Riders': 164,
    'Lucknow Super Giants': 160,'Mumbai Indians': 169,
    'Punjab Kings': 163,        'Rajasthan Royals': 162,
    'Royal Challengers Bengaluru': 168, 'Sunrisers Hyderabad': 158,
}

BOWLING_AVG = {
    'Chennai Super Kings': 163, 'Delhi Capitals': 165,
    'Gujarat Titans': 160,      'Kolkata Knight Riders': 164,
    'Lucknow Super Giants': 162,'Mumbai Indians': 161,
    'Punjab Kings': 167,        'Rajasthan Royals': 163,
    'Royal Challengers Bengaluru': 169, 'Sunrisers Hyderabad': 158,
}

HOME_CITY = {
    'Mumbai Indians': 'mumbai',
    'Chennai Super Kings': 'chennai',
    'Royal Challengers Bengaluru': 'bengaluru',
    'Kolkata Knight Riders': 'kolkata',
    'Delhi Capitals': 'delhi',
    'Sunrisers Hyderabad': 'hyderabad',
    'Rajasthan Royals': 'jaipur',
    'Punjab Kings': 'mohali',
    'Gujarat Titans': 'ahmedabad',
    'Lucknow Super Giants': 'lucknow',
}

VENUE_CITY = {
    'Wankhede Stadium': 'mumbai',
    'MA Chidambaram Stadium': 'chennai',
    'Eden Gardens': 'kolkata',
    'M Chinnaswamy Stadium': 'bengaluru',
    'Arun Jaitley Stadium': 'delhi',
    'Narendra Modi Stadium, Ahmedabad': 'ahmedabad',
    'Rajiv Gandhi International Cricket Stadium': 'hyderabad',
    'Sawai Mansingh Stadium': 'jaipur',
    'Punjab Cricket Association IS Bindra Stadium, Mohali': 'mohali',
    'Ekana Cricket Stadium': 'lucknow',
}

DEW_VENUES = [
    'Wankhede Stadium', 'Eden Gardens',
    'Rajiv Gandhi International Cricket Stadium',
    'Arun Jaitley Stadium', 'MA Chidambaram Stadium',
    'Ekana Cricket Stadium', 'Narendra Modi Stadium, Ahmedabad'
]

# ── Request schema ─────────────────────────────────────────────────────────
class MatchInput(BaseModel):
    batting_team : str
    bowling_team : str
    venue        : str
    toss_winner  : str
    month        : int
    year         : int = 2025

# ── Feature builder ────────────────────────────────────────────────────────
def build_features(data: MatchInput):
    venue_avg = VENUE_AVG.get(data.venue, 163)
    bat_avg   = TEAM_AVG.get(data.batting_team, 163)
    bowl_avg  = BOWLING_AVG.get(data.bowling_team, 163)
    toss_bat  = 1 if data.toss_winner == "batting" else 0
    dew       = 1 if data.venue in DEW_VENUES else 0
    modern    = 1 if data.year >= 2020 else 0
    home      = 1 if VENUE_CITY.get(data.venue) == HOME_CITY.get(data.batting_team) else 0

    try:    bat_enc   = int(le_team.transform([data.batting_team])[0])
    except: bat_enc   = 0
    try:    bowl_enc  = int(le_team.transform([data.bowling_team])[0])
    except: bowl_enc  = 0
    try:    venue_enc = int(le_venue.transform([data.venue])[0])
    except: venue_enc = 0

    base = {
        'venue_avg_score'      : venue_avg,
        'batting_team_avg'     : bat_avg,
        'batting_team_rolling' : bat_avg * 1.02,
        'toss_bat_first'       : toss_bat,
        'year'                 : data.year,
        'month'                : data.month,
        'batting_team_enc'     : bat_enc,
        'bowling_team_enc'     : bowl_enc,
        'venue_enc'            : venue_enc,
    }

    features_a = pd.DataFrame([base])
    features_b = pd.DataFrame([{
        **base,
        'dew_factor'               : dew,
        'batting_recent_form'      : bat_avg * 1.03,
        'form_ratio'               : 1.03,
        'h2h_avg'                  : (venue_avg + bat_avg) / 2,
        'bowling_team_avg_conceded': bowl_avg,
        'is_home_ground'           : home,
        'modern_era'               : modern,
    }])

    return features_a, features_b

# ── Routes ─────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "IPL Score Predictor API running", "models_loaded": models_ready}

@app.get("/health")
def health():
    # Returns instantly — never blocks
    return {"status": "healthy", "models_loaded": models_ready}

@app.get("/teams")
def get_teams():
    return {"teams": CURRENT_TEAMS}

@app.get("/venues")
def get_venues():
    return {"venues": CURRENT_VENUES}

@app.post("/predict")
def predict(data: MatchInput):
    if not models_ready:
        return {"error": "Models still loading — please wait a moment and retry."}

    t0 = time.time()
    features_a, features_b = build_features(data)

    # Each container only loads one model based on MODEL_STAGE
    if MODEL_STAGE == "Production":
        pred        = float(models["a"].predict(features_a)[0])
        algo, feats = "XGBoost v1.0", 9
    else:
        pred        = float(models["b"].predict(features_b)[0])
        algo, feats = "LightGBM v2.0", 16

    latency_ms = round((time.time() - t0) * 1000, 1)

    print(f"   /predict | {data.batting_team} vs {data.bowling_team} | stage={MODEL_STAGE} pred={round(pred)} | {latency_ms}ms")

    return {
        "match"     : f"{data.batting_team} vs {data.bowling_team}",
        "venue"     : data.venue,
        "stage"     : MODEL_STAGE,
        "algorithm" : algo,
        "features"  : feats,
        "prediction": round(pred),
        "latency_ms": latency_ms,
    }