import logging
from fastapi import APIRouter

from src.core.option_parser import (
    load_options_cache,
    build_options_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/llama-server", response_model=dict)
def get_server_options():
    cache = load_options_cache()
    return {"llama_server": cache.get("llama-server", [])}


@router.get("/llama-swap", response_model=dict)
def get_swap_options():
    cache = load_options_cache()
    return {"llama_swap": cache.get("llama-swap", [])}


@router.post("/refresh", response_model=dict)
def refresh_options():
    cache = build_options_cache()
    return {"success": True}
