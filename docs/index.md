# CLISApp — Project Documentation Index

This index is the primary entry point for understanding CLISApp for AI-assisted development.

## Quick Start (What to read first)

1) `project-overview.md`
2) `technology-stack.md`
3) `source-tree-analysis.md`
4) `integration-architecture.md`

## Architecture

- `architecture-patterns.md`
- `architecture-frontend.md`
- `architecture-backend.md`

## API Contracts

- `api-contracts-frontend.md`
- `api-contracts-backend.md`

## Data Models

- `data-models-frontend.md`
- `data-models-backend.md`

## Frontend UI + State

- `component-inventory-frontend.md`
- `state-management-frontend.md`
- `asset-inventory-frontend.md`

## Development & Operations

- `development-guide-frontend.md`
- `development-guide-backend.md`
- `deployment-guide.md`
- `contribution-guide.md`

## Repository Metadata

- `project-parts.json`
- `project-scan-report.json`
- `existing-documentation-inventory.md`

## Known Mismatches / Follow-ups

- Health endpoint path mismatch: frontend uses `/health` but backend API mounts under `/api/v1/health`.
- Tile URL shape mismatch: frontend generates URLs with `{level}` while phase-0 tile server omits it.

If planning new features, clarify these contracts first so PRD/stories reference a single canonical API surface.
