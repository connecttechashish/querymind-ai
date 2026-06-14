from querymindai_backend.pipeline.graph import QueryPipelineState, create_query_graph
from querymindai_backend.utils.tracing import trace_step

# Compile and cache the query graph workflow
_graph = create_query_graph()

def run_query_pipeline(question: str) -> QueryPipelineState:
    """
    Runs the full text-to-SQL analytics pipeline end-to-end using the compiled LangGraph workflow.
    Traces start and completion of the orchestrator run optionally.
    """
    initial_state: QueryPipelineState = {
        "question": question,
        "classification": None,
        "linked_schema": None,
        "examples": None,
        "generation": None,
        "validation": None,
        "execution": None,
        "formatted_result": None,
        "status": "pending",
        "error": None,
        "needs_clarification": False
    }
    
    # Trace orchestrator pipeline entry
    trace_step("orchestrator_start", {"question": question})
    
    try:
        # Execute graph invocation
        result = _graph.invoke(initial_state)
        
        # Trace orchestrator pipeline completion
        status = result.get("status", "unknown")
        trace_step("orchestrator_finish", {
            "question": question,
            "status": status,
            "error": result.get("error")
        })
        return result
    except Exception as e:
        # Trace orchestrator pipeline failure
        trace_step("orchestrator_exception", {
            "question": question,
            "error": str(e)
        })
        raise e
