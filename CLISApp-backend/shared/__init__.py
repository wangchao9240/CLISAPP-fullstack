"""
Shared utilities for both API and data pipeline.

This module provides common functionality that can be imported by both:
- CLISApp-backend/app/ (API service)
- CLISApp-backend/data_pipeline/ (data pipeline)

Architecture rule: This is the ONLY location for shared code.
- app/ MUST NOT import from data_pipeline/
- data_pipeline/ MUST NOT import from app/
- Both MAY import from shared/
"""
