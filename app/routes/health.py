import time
import requests
from fastapi import APIRouter, Response
from dotenv import load_dotenv
import os

health_router = APIRouter()


load_dotenv()

REGISTRY_URL = os.getenv("REGISTRY_URL")

DEFAULT_HEADERS = {
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Accept-Encoding": "identity",
}


@health_router.get("/liveness")
async def liveness_probe(response: Response):
    response.status_code = 200
    return {"status": "alive"}


@health_router.get("/readiness")
async def readiness_probe(response: Response):
    start_time = time.time()
    try:
        response = requests.get(f"{REGISTRY_URL}/v2/_catalog", headers=DEFAULT_HEADERS)
        response.raise_for_status()
        status = "ready"
        response_status = 200
    except requests.exceptions.RequestException:
        status = "unready"
        response_status = 500
    end_time = time.time()
    total_time_taken = end_time - start_time
    response.status_code = response_status
    return {"status": status, "total_time_taken": total_time_taken}
