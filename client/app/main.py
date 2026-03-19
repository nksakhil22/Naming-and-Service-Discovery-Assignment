from __future__ import annotations

import os
import random
import time
from typing import Any, Dict, List

import httpx


def _env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None or v == "":
        raise RuntimeError(f"Missing env var: {name}")
    return v


REGISTRY_URL = _env("REGISTRY_URL")
SERVICE_NAME = _env("SERVICE_NAME", "hello-service")
CALL_PATH = _env("CALL_PATH", "/hello")
INTERVAL_SECONDS = float(_env("INTERVAL_SECONDS", "2"))


def _pick_random(instances: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    if not instances:
        return None
    return random.choice(instances)


def _instance_url(inst: Dict[str, Any]) -> str:
    return f"http://{inst['host']}:{inst['port']}{CALL_PATH}"


def main():
    print(f"[client] registry={REGISTRY_URL} service={SERVICE_NAME} path={CALL_PATH} interval={INTERVAL_SECONDS}s")
    with httpx.Client(timeout=2.5) as client:
        while True:
            try:
                r = client.get(f"{REGISTRY_URL}/services/{SERVICE_NAME}")
                r.raise_for_status()
                instances = r.json()
            except Exception as e:
                print(f"[client] discovery failed: {e}")
                time.sleep(INTERVAL_SECONDS)
                continue

            inst = _pick_random(instances)
            if not inst:
                print("[client] no instances found")
                time.sleep(INTERVAL_SECONDS)
                continue

            url = _instance_url(inst)
            try:
                rr = client.get(url)
                rr.raise_for_status()
                body = rr.json()
                print(f"[client] -> {inst['instance_id']} @ {inst['host']}:{inst['port']} => {body}")
            except Exception as e:
                print(f"[client] call failed ({url}): {e}")

            time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

