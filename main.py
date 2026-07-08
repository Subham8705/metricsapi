from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
from jwt import InvalidTokenError
import uuid
import time

app = FastAPI()

# ============================================================
# Assignment 1 Configuration
# ============================================================

EMAIL = "24f2000610@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://dash-ck249g.example.com"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,
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

    nums = [int(x.strip()) for x in values.split(",")]

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