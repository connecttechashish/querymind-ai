import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def is_tracing_enabled() -> bool:
    """
    Checks if LangSmith tracing is enabled based on environment variables.
    Requires LANGCHAIN_TRACING_V2 to be set to truthy values and LANGCHAIN_API_KEY to be present.
    """
    tracing_env = os.environ.get("LANGCHAIN_TRACING_V2", "").lower()
    api_key = os.environ.get("LANGCHAIN_API_KEY", "")
    return tracing_env in ("true", "1", "yes") and bool(api_key.strip())

def trace_step(step_name: str, payload: Dict[str, Any]) -> None:
    """
    Traces a single step to LangSmith if tracing is enabled.
    Guarantees no failure is propagated to the main application if tracing fails.
    """
    if not is_tracing_enabled():
        return
        
    try:
        from langsmith import Client
        client = Client()
        client.create_run(
            name=step_name,
            run_type="chain",
            inputs=payload,
            outputs={}
        )
    except Exception as e:
        # Safe fallback logger output (app must never fail because tracing is missing or fails)
        logger.debug(f"Langsmith tracing failed for step '{step_name}': {e}")
