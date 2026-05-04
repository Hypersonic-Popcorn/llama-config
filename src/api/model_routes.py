import logging
import os

from fastapi import APIRouter

from src.core.model_scanner import scan_models
from src.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=list)
def list_models():
    return _models_cache

# Scan once at module load time (backend startup)
_models_cache = []
if not os.environ.get("TESTING"):
    _models = scan_models(settings.model_directory)
    _models_cache = [
        {
            "name": m.name,
            "architecture": m.architecture,
            "context_length": m.context_length,
            "parameter_count": m.parameter_count,
            "quantization": m.quantization,
            "file_size": m.file_size,
            "filename": m.filename,
            "full_path": m.full_path,
            "size": m.file_size,
            "quant": m.quantization,
        }
        for m in _models.models
    ]
