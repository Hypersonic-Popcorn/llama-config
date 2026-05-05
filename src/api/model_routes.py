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
    _models = scan_models(settings.model_dir)
    _models_cache = [
        {
            "name": m.name,
            "architecture": m.architecture,
            "basename": m.basename,
            "context_length": m.context_length,
            "parameter_count": m.parameter_count,
            "quantization": m.quantization_version,
            "quantization_version": m.quantization_version,
            "finetune": m.finetune,
            "license": m.license,
            "license_link": m.license_link,
            "sampling_temp": m.sampling_temp,
            "sampling_top_k": m.sampling_top_k,
            "sampling_top_p": m.sampling_top_p,
            "size_label": m.size_label,
            "model_type": m.model_type,
            "block_count": m.block_count,
            "file_size": m.file_size,
            "filename": m.filename,
            "full_path": m.full_path,
            "size": m.file_size,
            "quant": m.quantization_version,
        }
        for m in _models.models
    ]
