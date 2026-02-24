# Project Overview

## What is CLISApp?

CLISApp (Queensland Climate Information System) is a mobile mapping application that visualizes climate layers for Queensland, Australia. It combines localized climate data with health-relevant context to help residents make informed decisions about outdoor activities.

Users interact with a map UI and can:

- View base map tiles (OpenStreetMap)
- Overlay climate raster tiles (PM2.5, precipitation, UV, humidity, temperature)
- Search for regions (LGA/suburb) and view climate details/boundaries
- Save favorite locations (store exists, UI pending)

## Current State (Phase 1 Complete)

### What's Working

- **5 climate layers** rendered on map with color-coded overlays and legends
- **Region search** with boundary display and climate data panel
- **Unified data pipeline** fetching all layers from Open-Meteo API (replaced legacy Copernicus CAMS / NASA GEOS-CF file downloads)
- **Automated scheduling** via cron (every 4 hours in production)
- **Cloud deployment** on GCloud (`136.114.38.138`) with systemd services
- **Dual platform** — iOS and Android builds functional

### What's Not Yet Built (Phase 2 Scope)

- User accounts / authentication
- Health insights and alerts (WHO/Australian standard-based advisories)
- Push notifications
- Favorites UI (store exists but no screen)
- Navigation beyond single MapScreen

## Data Pipeline

All climate data is sourced from the **Open-Meteo API** (free, no authentication required):

| Layer | API Parameter | Unit | Range |
|-------|--------------|------|-------|
| PM2.5 | `pm2_5` | µg/m³ | 0–500 |
| UV Index | `uv_index` | UVI | 0–15 |
| Temperature | `temperature_2m` | °C | -10–50 |
| Humidity | `relative_humidity_2m` | % | 0–100 |
| Precipitation | `precipitation` | mm | 0–100 |

**Pipeline flow:** Open-Meteo API → JSON (1,260 grid points) → GeoTIFF → PNG tiles (zoom 6–11)

**Grid coverage:** Queensland (-10° to -29° lat, 138° to 154° lon), ~50km resolution

Legacy data sources (Copernicus CAMS, NASA GEOS-CF, GPM IMERG) are archived in `_legacy/` and no longer used.

## Repository Structure

- **Frontend (mobile):** `CLISApp-frontend/` — React Native + TypeScript
- **Backend (API + tiles + pipeline):** `CLISApp-backend/` — FastAPI + Python

## Runtime Topology (Local Dev)

- **API service:** `http://localhost:8080` — JSON endpoints (`/api/v1/*`)
- **Tile server:** `http://localhost:8000` — PNG tile delivery (`/tiles/{layer}/{z}/{x}/{y}.png`)
- **Platform networking:** iOS uses `localhost`, Android uses `10.0.2.2`

## Key Documentation

- Technology stack: `technology-stack.md`
- Architecture: `architecture-frontend.md`, `architecture-backend.md`
- API contracts: `api-contracts-frontend.md`, `api-contracts-backend.md`
- Data models: `data-models-frontend.md`, `data-models-backend.md`
- Integration: `integration-architecture.md`
- Deployment: `deployment-guide.md`
