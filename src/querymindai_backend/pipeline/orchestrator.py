from querymindai_backend.pipeline.graph import QueryPipelineState, create_query_graph

# Compile and cache the query graph workflow
_graph = create_query_graph()

def run_query_pipeline(question: str) -> QueryPipelineState:
    """
    Runs the full text-to-SQL analytics pipeline end-to-end using the compiled LangGraph workflow.
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
    
    # Execute graph invocation
    result = _graph.invoke(initial_state)
    
    # Ensure we return a dictionary conforming to QueryPipelineState structure
    return result
