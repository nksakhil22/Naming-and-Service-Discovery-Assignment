from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    service: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)
    host: str = Field(min_length=1)
    port: int = Field(ge=1, le=65535)
    meta: Dict[str, str] = Field(default_factory=dict)
    ttl_seconds: int = Field(default=10, ge=2, le=300)


class Instance(BaseModel):
    service: str
    instance_id: str
    host: str
    port: int
    meta: Dict[str, str] = Field(default_factory=dict)
    last_heartbeat: float
    ttl_seconds: int

    def is_alive(self, now: float) -> bool:
        return (now - self.last_heartbeat) <= self.ttl_seconds


class HeartbeatRequest(BaseModel):
    service: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)


class DeregisterRequest(BaseModel):
    service: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)


app = FastAPI(title="Simple Service Registry", version="1.0")

# In-memory registry:
# services[service_name][instance_id] = Instance
services: Dict[str, Dict[str, Instance]] = {}
lock = asyncio.Lock()


@app.get("/health")
async def health():
    return {"ok": True, "ts": time.time()}


@app.post("/register")
async def register(req: RegisterRequest):
    now = time.time()
    inst = Instance(
        service=req.service,
        instance_id=req.instance_id,
        host=req.host,
        port=req.port,
        meta=req.meta,
        last_heartbeat=now,
        ttl_seconds=req.ttl_seconds,
    )
    async with lock:
        services.setdefault(req.service, {})[req.instance_id] = inst
    return {"registered": True, "instance": inst.model_dump()}


@app.post("/heartbeat")
async def heartbeat(req: HeartbeatRequest):
    now = time.time()
    async with lock:
        svc = services.get(req.service)
        if not svc or req.instance_id not in svc:
            raise HTTPException(status_code=404, detail="Instance not found")
        svc[req.instance_id].last_heartbeat = now
    return {"ok": True, "ts": now}


@app.post("/heartbeat/{service_name}/{instance_id}")
async def heartbeat_path(service_name: str, instance_id: str):
    # Path-based heartbeat so registry access logs show service + instance_id
    return await heartbeat(HeartbeatRequest(service=service_name, instance_id=instance_id))


@app.post("/deregister")
async def deregister(req: DeregisterRequest):
    async with lock:
        svc = services.get(req.service)
        if not svc or req.instance_id not in svc:
            return {"removed": False}
        del svc[req.instance_id]
        if not svc:
            services.pop(req.service, None)
    return {"removed": True}


@app.get("/services/{service_name}")
async def list_instances(service_name: str, healthy_only: bool = True) -> List[dict]:
    now = time.time()
    async with lock:
        svc = services.get(service_name, {})
        instances = list(svc.values())

    if healthy_only:
        instances = [i for i in instances if i.is_alive(now)]

    return [i.model_dump() for i in instances]


@app.get("/discover/{service_name}")
async def discover(service_name: str, healthy_only: bool = True) -> dict:
    instances = await list_instances(service_name=service_name, healthy_only=healthy_only)
    return {"service": service_name, "count": len(instances), "instances": instances}


async def _reaper_loop():
    while True:
        await asyncio.sleep(1)
        now = time.time()
        async with lock:
            to_delete_services: List[str] = []
            for svc_name, inst_map in services.items():
                dead = [iid for iid, inst in inst_map.items() if not inst.is_alive(now)]
                for iid in dead:
                    del inst_map[iid]
                if not inst_map:
                    to_delete_services.append(svc_name)
            for svc_name in to_delete_services:
                del services[svc_name]


@app.on_event("startup")
async def _startup():
    asyncio.create_task(_reaper_loop())

