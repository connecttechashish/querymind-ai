from contextlib import asynccontextmanager
from fastapi import FastAPI
from querymindai_backend.config import get_settings
from querymindai_backend.logging_config import setup_logging
from querymindai_backend.models import RootResponse, HealthResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Call setup_logging at startup
    setup_logging()
    yield

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)

@app.get("/", response_model=RootResponse)
async def read_root() -> RootResponse:
    return RootResponse(
        message="Welcome to the QueryMind AI API",
        app_name=settings.app_name,
        version=settings.app_version,
    )

@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
