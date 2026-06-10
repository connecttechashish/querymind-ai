import re
import sqlite3
from pydantic import BaseModel
from typing import List, Set
from querymindai_backend.database import get_admin_db_connection

class RetrievedExample(BaseModel):
    question: str
    sql: str
    query_type: str
    score: float

def tokenize(text: str) -> Set[str]:
    """
    Lowercases and splits the text into a set of alphanumeric words.
    """
    return set(re.findall(r"\b\w+\b", text.lower()))

def retrieve_examples(question: str, top_k: int = 3) -> List[RetrievedExample]:
    """
    Reads few-shot examples from admin_config.db and retrieves the top_k
    closest examples using Jaccard keyword overlap similarity.
    """
    query_tokens = tokenize(question)
    if not query_tokens:
        return []

    try:
        conn = get_admin_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT question, sql_query, query_type FROM few_shot_examples WHERE is_active = 1;")
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        # Gracefully handle non-initialized table
        rows = []
    finally:
        if "conn" in locals():
            conn.close()

    retrieved = []
    for row in rows:
        ex_question = row["question"]
        ex_sql = row["sql_query"]
        ex_type = row["query_type"]
        
        ex_tokens = tokenize(ex_question)
        intersection = query_tokens.intersection(ex_tokens)
        union = query_tokens.union(ex_tokens)
        score = len(intersection) / len(union) if union else 0.0
        
        retrieved.append(
            RetrievedExample(
                question=ex_question,
                sql=ex_sql,
                query_type=ex_type,
                score=round(score, 4)
            )
        )

    # Sort descending by similarity score, fallback on question text for deterministic order
    retrieved.sort(key=lambda x: (-x.score, x.question))
    
    return retrieved[:top_k]
