import logging
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.config_routes import router as config_router
from src.api.model_routes import router as model_router
from src.api.docker_routes import router as docker_router
from src.api.options_routes import router as options_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/llama-config.log"),
        logging.StreamHandler(),
    ],
)

app = FastAPI(title="llama-config", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "type": type(exc).__name__},
    )


app.include_router(config_router, prefix="/api/config")
app.include_router(model_router, prefix="/api/models")
app.include_router(docker_router, prefix="/api/docker")
app.include_router(options_router, prefix="/api/options")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
