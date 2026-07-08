from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

app = FastAPI()

ALLOWED_ORIGIN = "https://dash-ck249g.example.com"

app.add_middleware(
	CORSMiddleware,
	allow_origins=[ALLOWED_ORIGIN],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

EMAIL = "24f2000610@ds.study.iitm.ac.in"


@app.middleware("http")
async def add_headers(request: Request, call_next):
	start = time.perf_counter()

	response = await call_next(request)

	process_time = time.perf_counter() - start

	response.headers["X-Request-ID"] = str(uuid.uuid4())
	response.headers["X-Process-Time"] = str(process_time)

	return response


@app.get("/")
def root():
	return {"status": "running"}


@app.get("/stats")
def stats(values: str):
	nums = [int(x) for x in values.split(",")]

	return {
		"email": EMAIL,
		"count": len(nums),
		"sum": sum(nums),
		"min": min(nums),
		"max": max(nums),
		"mean": sum(nums) / len(nums),
	}
