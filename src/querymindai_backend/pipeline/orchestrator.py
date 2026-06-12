from querymindai_backend.pipeline.graph import QueryPipelineState, create_query_graph

# Compile the LangGraph query execution graph at module load time
_graph = create_query_graph()

def run_query_pipeline(question: str) -> QueryPipelineState:
    """
    Runs the text-to-SQL analytics pipeline end-to-end using the compiled LangGraph workflow.
    
    Flow:
    1. classify_query intent
    2. if unsupported query type, route to END
    3. link_schema and synonyms
    4. if ambiguities found, route to END (clarification status)
    5. retrieve few-shot examples
    6. generate SQL
    7. validate SQL
    8. if invalid SQL generated, route to END
    9. execute SQL on read-only connection
    10. format columns and rows into final formatted response
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
    
    return _graph.invoke(initial_state)
