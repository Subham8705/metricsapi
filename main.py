from fastapi import FastAPI, Request, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List
import jwt
from jwt import InvalidTokenError
import uuid
import time
import os
import yaml
import datetime
from dotenv import dotenv_values

app = FastAPI()

STARTUP_TIME = time.time()
http_requests_total = 0
request_logs = []

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
    expose_headers=["*"],
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
    global http_requests_total
    http_requests_total += 1

    start = time.perf_counter()

    response = await call_next(request)

    process_time = time.perf_counter() - start

    request_id = str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    log_entry = {
        "level": "info",
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "path": request.url.path,
        "request_id": request_id
    }
    request_logs.append(log_entry)

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


# ============================================================
# Assignment 6: Observability
# ============================================================

@app.get("/work")
def work(n: int):
    # Do K units of work, return email and n
    return {"email": EMAIL, "done": n}

@app.get("/metrics")
def metrics():
    content = f"# HELP http_requests_total Total number of HTTP requests\n# TYPE http_requests_total counter\nhttp_requests_total {http_requests_total}\n"
    return PlainTextResponse(content=content)

@app.get("/healthz")
def healthz():
    uptime_s = time.time() - STARTUP_TIME
    return {"status": "ok", "uptime_s": uptime_s}

@app.get("/logs/tail")
def logs_tail(limit: int = 10):
    return request_logs[-limit:]


# ============================================================
# API Engineering Patterns (Orders API)
# ============================================================

import base64

# --- 1. Rate Limiting ---
client_requests = {}
RATE_LIMIT_R = 17
RATE_LIMIT_WINDOW = 10.0

def rate_limit(x_client_id: str = Header(None)):
    client_id = x_client_id or "anonymous"
    now = time.time()
    
    if client_id not in client_requests:
        client_requests[client_id] = []
        
    timestamps = client_requests[client_id]
    timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]
    
    if len(timestamps) >= RATE_LIMIT_R:
        retry_after = int(RATE_LIMIT_WINDOW - (now - timestamps[0]))
        if retry_after < 1:
            retry_after = 1
        client_requests[client_id] = timestamps
        raise HTTPException(
            status_code=429, 
            detail="Too Many Requests", 
            headers={"Retry-After": str(retry_after)}
        )
        
    timestamps.append(now)
    client_requests[client_id] = timestamps
    return client_id

# --- 2. Cursor Pagination ---
TOTAL_ORDERS = 60
catalog = [{"id": i} for i in range(1, TOTAL_ORDERS + 1)]

def encode_cursor(idx: int) -> str:
    return base64.b64encode(str(idx).encode("utf-8")).decode("utf-8")

def decode_cursor(cursor: str) -> int:
    try:
        return int(base64.b64decode(cursor.encode("utf-8")).decode("utf-8"))
    except:
        return 0

@app.get("/orders")
def get_orders(limit: int = 10, cursor: str = None, client_id: str = Depends(rate_limit)):
    start_idx = 0
    if cursor:
        start_idx = decode_cursor(cursor)
        
    items = catalog[start_idx:start_idx + limit]
    
    next_idx = start_idx + len(items)
    next_cursor = None
    if next_idx < len(catalog):
        next_cursor = encode_cursor(next_idx)
        
    return {
        "items": items,
        "next_cursor": next_cursor
    }

# --- 3. Idempotent POST ---
idempotent_store = {}
order_id_counter = 1000

@app.post("/orders", status_code=201)
def create_order(request: Request, idempotency_key: str = Header(...), client_id: str = Depends(rate_limit)):
    global order_id_counter
    if idempotency_key in idempotent_store:
        return idempotent_store[idempotency_key]
    
    order_id_counter += 1
    order_data = {"id": str(order_id_counter)}
    idempotent_store[idempotency_key] = order_data
    return order_data