from __future__ import annotations

import asyncio
import os
import socket
import time
from typing import Any, Dict

import httpx
from fastapi import FastAPI


def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing env var: {name}")
    return v


REGISTRY_URL = _env("REGISTRY_URL")
SERVICE_NAME = _env("SERVICE_NAME", "hello-service")
SERVICE_HOST = _env("SERVICE_HOST", socket.gethostname())
SERVICE_PORT = int(_env("SERVICE_PORT", "8080"))
INSTANCE_ID = _env("INSTANCE_ID", f"{SERVICE_NAME}-{SERVICE_HOST}-{SERVICE_PORT}")
TTL_SECONDS = int(os.getenv("TTL_SECONDS", "10"))


app = FastAPI(title=f"{SERVICE_NAME} ({INSTANCE_ID})", version="1.0")


@app.get("/health")
async def health():
    return {"ok": True, "service": SERVICE_NAME, "instance_id": INSTANCE_ID, "ts": time.time()}


@app.get("/hello")
async def hello():
    return {
        "message": "hello",
        "service": SERVICE_NAME,
        "instance_id": INSTANCE_ID,
        "host": SERVICE_HOST,
        "port": SERVICE_PORT,
        "ts": time.time(),
    }


async def _register_and_heartbeat_loop():
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                await client.post(
                    f"{REGISTRY_URL}/register",
                    json={
                        "service": SERVICE_NAME,
                        "instance_id": INSTANCE_ID,
                        "host": SERVICE_HOST,
                        "port": SERVICE_PORT,
                        "meta": {"kind": "demo"},
                        "ttl_seconds": TTL_SECONDS,
                    },
                )
                break
            except Exception:
                await asyncio.sleep(0.5)

        while True:
            try:
                await client.post(
                    f"{REGISTRY_URL}/heartbeat/{SERVICE_NAME}/{INSTANCE_ID}",
                )
            except Exception:
                # If registry is temporarily unavailable, keep retrying; TTL will eventually expire otherwise.
                pass
            await asyncio.sleep(max(1, TTL_SECONDS // 2))


@app.on_event("startup")
async def _startup():
    asyncio.create_task(_register_and_heartbeat_loop())


@app.on_event("shutdown")
async def _shutdown():
    # Best-effort deregistration (not guaranteed on hard kills)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            await client.post(
                f"{REGISTRY_URL}/deregister",
                json={"service": SERVICE_NAME, "instance_id": INSTANCE_ID},
            )
    except Exception:
        pass

