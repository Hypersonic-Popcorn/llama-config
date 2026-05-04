import logging
from fastapi import APIRouter

from src.core.model_scanner import scan_models
from src.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=dict)
def list_models():
    result = scan_models(settings.model_directory)
    return {
        "models": [
            {
                "name": m.name,
                "architecture": m.architecture,
                "context_length": m.context_length,
                "parameter_count": m.parameter_count,
                "quantization": m.quantization,
                "file_size": m.file_size,
                "filename": m.filename,
                "full_path": m.full_path,
            }
            for m in result.models
        ],
        "errors": result.errors,
    }
