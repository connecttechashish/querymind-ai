from typing import TypedDict, List, Optional
from querymindai_backend.pipeline.classifier import ClassifierResult
from querymindai_backend.pipeline.linker import SchemaLinkResult
from querymindai_backend.pipeline.retriever import RetrievedExample
from querymindai_backend.pipeline.generator import SQLGenerationResult
from querymindai_backend.pipeline.validator import SQLValidationResult
from querymindai_backend.pipeline.executor import SQLExecutionResult
from querymindai_backend.pipeline.formatter import FormatResult

class QueryPipelineState(TypedDict, total=False):
    """
    State definition for the LangGraph query execution pipeline.
    Allows partial updates at each stage of the pipeline graph.
    """
    question: str
    classification: Optional[ClassifierResult]
    linked_schema: Optional[SchemaLinkResult]
    examples: Optional[List[RetrievedExample]]
    generation: Optional[SQLGenerationResult]
    validation: Optional[SQLValidationResult]
    execution: Optional[SQLExecutionResult]
    formatted_result: Optional[FormatResult]
    status: str
    error: Optional[str]
    needs_clarification: bool
