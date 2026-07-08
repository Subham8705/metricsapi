from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import jwt
from jwt import InvalidTokenError
import uuid
import time
import os
import yaml
from dotenv import dotenv_values

app = FastAPI()

# ============================================================
# Assignment 1 Configuration
# ============================================================

EMAIL = "24f2000610@ds.study.iitm.ac.in"

# ALLOWED_ORIGIN = "https://dash-ck249g.example.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://dash-ck249g.example.com",
        "https://exam.sanand.workers.dev",
        "https://exam.sanand.workers.dev/"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Assignment 2 Configuration
# ============================================================

ISSUER = "https://idp.exam.local"

AUDIENCE = "tds-x948scxi.apps.exam.local"

PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----
"""


DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000"
}


def to_bool(v):
    if isinstance(v, bool):
        return v
    return str(v).lower() in ["true", "1", "yes", "on"]


def cast_value(key, value):
    if key in ["port", "workers"]:
        return int(value)
    if key == "debug":
        return to_bool(value)
    return str(value)


# ============================================================
# Middleware
# ============================================================

@app.middleware("http")
async def add_headers(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = str(process_time)

    return response

# ============================================================
# Root
# ============================================================

@app.get("/")
def root():
    return {
        "message": "API is running"
    }

# ============================================================
# Assignment 1
# ============================================================

@app.get("/stats")
def stats(values: str):
    try:
        nums = [int(x.strip()) for x in values.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid values parameter; expected comma-separated integers"
        )

    if not nums:
        raise HTTPException(
            status_code=400,
            detail="Values query parameter cannot be empty"
        )

    return {
        "email": EMAIL,
        "count": len(nums),
        "sum": sum(nums),
        "min": min(nums),
        "max": max(nums),
        "mean": sum(nums) / len(nums),
    }

# ============================================================
# Assignment 2
# ============================================================

class TokenRequest(BaseModel):
    token: str


@app.post("/verify")
def verify(req: TokenRequest):

    try:

        payload = jwt.decode(
            req.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            issuer=ISSUER,
            audience=AUDIENCE,
        )

        return {
            "valid": True,
            "email": payload.get("email"),
            "sub": payload.get("sub"),
            "aud": payload.get("aud"),
        }

    except InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail={
                "valid": False
            }
        )
    

@app.get("/effective-config")
def effective_config(request: Request):

    config = DEFAULTS.copy()

    # ------------------------------------------------
    # YAML
    # ------------------------------------------------

    if os.path.exists("config.development.yaml"):
        with open("config.development.yaml") as f:
            y = yaml.safe_load(f)

            if y:
                config.update(y)

    # ------------------------------------------------
    # .env
    # ------------------------------------------------

    env_values = dotenv_values(".env")
    env_mapping = {
        "APP_LOG_LEVEL": "log_level",
        "NUM_WORKERS": "workers",
        "APP_PORT": "port",
        "APP_DEBUG": "debug",
        "APP_API_KEY": "api_key"
    }
    for k, v in env_values.items():
        if v is None:
            continue
            
        if k in env_mapping:
            key = env_mapping[k]
            config[key] = cast_value(key, v)

    # ------------------------------------------------
    # OS ENV
    # ------------------------------------------------

    for k, v in os.environ.items():

        if not k.startswith("APP_"):
            continue

        key = k[4:].lower()
        config[key] = cast_value(key, v)

    # ------------------------------------------------
    # CLI overrides
    # ------------------------------------------------

    for item in request.query_params.getlist("set"):

        if "=" not in item:
            continue

        k, v = item.split("=", 1)

        config[k] = cast_value(k, v)

    # ------------------------------------------------
    # Secret masking
    # ------------------------------------------------

    config["api_key"] = "*****"
    
    allowed_keys = ["port", "workers", "debug", "log_level", "api_key"]
    return {k: config[k] for k in allowed_keys if k in config}


# ============================================================
# Analytics Endpoint
# ============================================================

class Event(BaseModel):
    user: str
    amount: float
    ts: int

class AnalyticsRequest(BaseModel):
    events: List[Event]

@app.post("/analytics")
def analytics(request: AnalyticsRequest, x_api_key: str = Header(None)):
    if x_api_key != "ak_rni7hj0lv3qn8jhl781wjxon":
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    
    events = request.events
    total_events = len(events)
    unique_users = len(set(e.user for e in events))
    revenue = sum(e.amount for e in events if e.amount > 0)
    
    user_revenues = {}
    for e in events:
        if e.amount > 0:
            user_revenues[e.user] = user_revenues.get(e.user, 0) + e.amount
            
    top_user = max(user_revenues, key=user_revenues.get) if user_revenues else ""
    
    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": unique_users,
        "revenue": revenue,
        "top_user": top_user
    }