import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from querymindai_backend.config import get_settings
from querymindai_backend.logging_config import setup_logging
from querymindai_backend.models import RootResponse, HealthResponse, QueryRequest, QueryResponse
from querymindai_backend.pipeline.orchestrator import run_query_pipeline
from querymindai_backend.middleware import RequestIDMiddleware

# Import Admin Routers
from querymindai_backend.admin.schema_routes import router as schema_router
from querymindai_backend.admin.examples_routes import router as examples_router
from querymindai_backend.admin.logs_routes import router as logs_router
from querymindai_backend.admin.guardrails_routes import router as guardrails_router
from querymindai_backend.admin.config_routes import router as config_router

logger = logging.getLogger("querymindai_backend.app")

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

# Register Request ID Middleware
app.add_middleware(RequestIDMiddleware)

# Register Admin Routers
app.include_router(schema_router)
app.include_router(examples_router)
app.include_router(logs_router)
app.include_router(guardrails_router)
app.include_router(config_router)

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catches all unhandled exceptions, logs them with stacktrace locally,
    and returns a sanitized error message to the client.
    """
    logger.error(f"Global unhandled exception: {exc}", exc_info=True)
    
    request_id = None
    if hasattr(request.state, "request_id"):
        request_id = request.state.request_id
    elif "x-request-id" in request.headers:
        request_id = request.headers["x-request-id"]
        
    content = {
        "status": "error",
        "message": "An internal server error occurred."
    }
    if request_id:
        content["request_id"] = request_id
        
    return JSONResponse(
        status_code=500,
        content=content
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

@app.get("/live")
async def liveness_check():
    """
    Liveness probe to verify that the application container is running.
    """
    return {"status": "live", "message": "App is running"}

@app.get("/ready")
async def readiness_check():
    """
    Readiness probe to check if all configurations and components load successfully.
    """
    try:
        settings_test = get_settings()
        # Verify basic config parameters access
        _ = settings_test.db_path
        return {"status": "ready", "message": "App is ready to process queries"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Configuration failed to load: {str(e)}"
        )

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest) -> QueryResponse:
    """
    Executes a natural language analytics query end-to-end and returns the structured results.
    """
    try:
        pipeline_res = run_query_pipeline(req.question)
    except Exception as e:
        return QueryResponse(
            status="failed",
            question=req.question,
            error=f"Pipeline exception occurred: {str(e)}",
            needs_clarification=False
        )

    status = pipeline_res.get("status", "failed")
    error = pipeline_res.get("error")
    needs_clarification = pipeline_res.get("needs_clarification", False)

    # Conditionally extract generated SQL
    sql = None
    if req.include_sql and pipeline_res.get("generation"):
        val = pipeline_res.get("validation")
        if val and val.valid and val.sanitized_sql:
            sql = val.sanitized_sql
        else:
            sql = pipeline_res["generation"].sql

    # Conditionally extract explanation
    explanation = None
    if req.include_explanation and pipeline_res.get("generation"):
        explanation = pipeline_res["generation"].explanation

    # Extract formatted tables and summary
    table = None
    nl_summary = None
    fmt = pipeline_res.get("formatted_result")
    if fmt:
        table = fmt.data
        nl_summary = fmt.summary

    # Extract latency and row metrics
    row_count = 0
    latency_ms = 0.0
    exec_res = pipeline_res.get("execution")
    if exec_res:
        row_count = exec_res.row_count
        latency_ms = exec_res.latency_ms

    return QueryResponse(
        status=status,
        question=req.question,
        sql=sql,
        explanation=explanation,
        table=table,
        nl_summary=nl_summary,
        row_count=row_count,
        latency_ms=latency_ms,
        error=error,
        needs_clarification=needs_clarification
    )
