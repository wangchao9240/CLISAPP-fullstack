# Project Overview

## What is CLISApp?

CLISApp (Queensland Climate Information System) is a mobile mapping application that visualizes climate layers for Queensland.

Users interact with a map UI and can:

- View base map tiles (OpenStreetMap)
- Overlay climate raster tiles (PM2.5, precipitation, UV, humidity, temperature)
- Search for regions (LGA/suburb) and view details/boundaries

## Repository Structure

- **Frontend (mobile):** `CLISApp-frontend/` (React Native)
- **Backend (API + tiles + pipeline):** `CLISApp-backend/` (FastAPI + geospatial stack)

## Local Development Topology

- API service: `http://localhost:8080`
  - Primary API router prefix: `/api/v1`

- Tile server: `http://localhost:8000`
  - Tile routes: `/tiles/*`

## Key Documentation (Generated)

- Technology stack: `technology-stack.md`
- Architecture patterns: `architecture-patterns.md`
- Source tree analysis: `source-tree-analysis.md`
- Per-part architecture:
  - `architecture-frontend.md`
  - `architecture-backend.md`
- Per-part API contracts:
  - `api-contracts-frontend.md`
  - `api-contracts-backend.md`
- Per-part data models:
  - `data-models-frontend.md`
  - `data-models-backend.md`
- Frontend component inventory: `component-inventory-frontend.md`
- Integration architecture: `integration-architecture.md`
- Dev guides:
  - `development-guide-frontend.md`
  - `development-guide-backend.md`
- Deployment: `deployment-guide.md`

## Known Areas to Validate

- Health endpoint prefix mismatch (`/health` vs `/api/v1/health`).
- Tile URL shape mismatch between phase-0 tile server and main API tile endpoints.

These should be clarified before extending features that depend on them.
