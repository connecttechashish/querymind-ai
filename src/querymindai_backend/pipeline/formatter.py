from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class FormatResult(BaseModel):
    data: List[Dict[str, Any]] = Field(default_factory=list)
    summary: str
    suggested_chart: Optional[Dict[str, Any]] = None

def format_result(columns: List[str], rows: List[List[Any]]) -> FormatResult:
    """
    Formats the raw SQL execution columns and rows into a structured JSON-compatible response.
    
    1. Converts columns and rows into a list of dictionaries.
    2. Computes a simple summary: "Returned X rows."
    3. Detects if there is exactly one text column and one numeric column,
       and if so, suggests a bar chart.
    """
    # 1. Convert columns + rows into list of dictionaries
    data = []
    for row in rows:
        data.append(dict(zip(columns, row)))
        
    # 2. Add simple summary
    summary = f"Returned {len(rows)} rows."
    
    # 3. Suggest chart if exactly one text column and one numeric column
    suggested_chart = None
    if rows and columns:
        text_cols = []
        numeric_cols = []
        
        for idx, col_name in enumerate(columns):
            # Extract non-None values to determine the type
            non_none_vals = [row[idx] for row in rows if row[idx] is not None]
            
            if not non_none_vals:
                continue
            
            is_numeric = all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in non_none_vals)
            is_text = all(isinstance(v, str) for v in non_none_vals)
            
            if is_numeric:
                numeric_cols.append(col_name)
            elif is_text:
                text_cols.append(col_name)
                
        if len(text_cols) == 1 and len(numeric_cols) == 1:
            suggested_chart = {
                "type": "bar",
                "x": text_cols[0],
                "y": numeric_cols[0]
            }
            
    return FormatResult(
        data=data,
        summary=summary,
        suggested_chart=suggested_chart
    )
