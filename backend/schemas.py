# schemas.py
"""
Pydantic schemas for structured outputs in the RAG system.
This module contains all the structured output models used throughout the application.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime


class QueryMetadata(BaseModel):
    """Schema for extracting metadata from user queries."""
    doc_id: str = Field(
        description="Document ID or logical document name mentioned in the query. Use 'unknown' if not found."
    )
    version: str = Field(
        description="Version mentioned in the query (e.g., 'v1', 'v2', 'latest'). Use 'unknown' if not found."
    )
    effective_date: str = Field(
        description="Date or effective date mentioned in the query (YYYY-MM-DD format). Use 'unknown' if not found."
    )


class DocumentGrade(BaseModel):
    """Schema for document relevance grading."""
    grade: Literal["yes", "no"] = Field(
        description="Whether the retrieved documents are relevant to answer the user's question. 'yes' if relevant, 'no' if not relevant."
    )


class GeneratedAnswer(BaseModel):
    """Schema for generated answers from the RAG system."""
    answer: str = Field(
        description="The comprehensive answer to the user's question based on the retrieved documents."
    )
    sources_used: Optional[List[str]] = Field(
        default=None,
        description="List of document IDs or sources that were primarily used to generate the answer."
    )


class MetadataInference(BaseModel):
    """Schema for intelligent metadata inference from queries and available data."""
    doc_id: str = Field(
        description="Best matching document ID from available options, or 'unknown' if no good match."
    )
    version: str = Field(
        description="Best matching version from available options, or 'unknown' if no good match."
    )
    effective_date: str = Field(
        description="Best matching effective date from available options, or 'unknown' if no good match."
    )


class RewrittenQuery(BaseModel):
    """Schema for query rewriting when initial retrieval fails."""
    rewritten_query: str = Field(
        description="A paraphrased and improved version of the original query that might retrieve better documents."
    )
    reasoning: str = Field(
        description="Brief explanation of why the query was rewritten this way."
    )
