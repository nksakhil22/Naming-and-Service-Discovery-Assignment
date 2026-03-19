from __future__ import annotations

import os
import random
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query


def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing env var: {name}")
    return v


REGISTRY_URL = _env("REGISTRY_URL")
DEFAULT_SERVICE_NAME = os.getenv("DEFAULT_SERVICE_NAME", "hello-service")
DEFAULT_CALL_PATH = os.getenv("DEFAULT_CALL_PATH", "/hello")

app = FastAPI(title="Client (Discovery + Random Call)", version="1.0")


def _pick_random(instances: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not instances:
        return None
    return random.choice(instances)


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/call")
async def call(
    service: str = Query(default=DEFAULT_SERVICE_NAME, min_length=1),
    path: str = Query(default=DEFAULT_CALL_PATH, min_length=1),
):
    async with httpx.AsyncClient(timeout=3.0) as client:
        r = await client.get(f"{REGISTRY_URL}/services/{service}")
        r.raise_for_status()
        instances = r.json()

        inst = _pick_random(instances)
        if not inst:
            raise HTTPException(status_code=503, detail=f"no instances for service '{service}'")

        url = f"http://{inst['host']}:{inst['port']}{path}"
        rr = await client.get(url)
        rr.raise_for_status()

        resp_json: Any
        try:
            resp_json = rr.json()
        except Exception:
            resp_json = rr.text

        return {
            "service": service,
            "known_instances": len(instances),
            "chosen_instance_id": inst.get("instance_id"),
            "chosen_url": url,
            "response": resp_json,
        }

