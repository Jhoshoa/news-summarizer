from pathlib import Path

import yaml
from fastapi import APIRouter

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "sources.yaml"


def create_sources_router() -> APIRouter:
    router = APIRouter(prefix="/api/sources", tags=["sources"])

    @router.get("")
    async def get_sources():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {"items": data.get("sources", [])}

    return router
