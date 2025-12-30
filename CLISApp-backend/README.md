# CLISApp Backend

Queensland Climate Information System Backend – FastAPI services for climate tiles, region search, and health/status monitoring. This document explains the project structure, local setup, service start commands, and troubleshooting advice for both the API and tile server.

---

## ⚡ Quick Start (Recommended)

**Launch all services with one command:**

```bash
cd CLISApp-backend
./start.sh
```

Or run the Python script directly:

```bash
python start_all_services.py
```

This will start both:
- 📡 Main API Service (port 8080) - `/api/v1/` routes
- 🗺️ Tile Server (port 8000) - `/tiles/` tile service

---

## 1. Features at a Glance

- **Region API** (`app.main:app` - port 8080)
  - Region search, info, nearby queries, and health endpoints.
  - Mock data preloaded for Queensland LGAs and suburbs.
  - Base URL: `http://localhost:8080`
  - API Docs: `http://localhost:8080/docs`

- **Tile Server** (`data_pipeline.servers.tile_server:app` - port 8000)
  - Serves PNG tiles for climate layers (PM2.5, temperature, UV, humidity, precipitation).
  - Provides demo page, tile metadata, and transparent placeholders for missing tiles.
  - Base URL: `http://localhost:8000`
  - API Docs: `http://localhost:8000/docs`
  - Demo Page: `http://localhost:8000/tiles/pm25/demo`

- **Shared utilities**
  - Centralised configuration via `app/core/config.py` (Pydantic settings).
  - Tile and region business logic in `app/services`.
  - Data directories for downloads, processing artefacts, and generated tiles.

---

## 2. Project Structure

```
CLISApp-backend/
├── app/
│   ├── api/v1/           # FastAPI routers (health, tiles, regions, …)
│   ├── core/             # Settings & logging configuration
│   ├── models/           # Pydantic schemas for API responses
│   ├── services/         # Tile + region domain logic
│   ├── utils/            # Helpers for file paths, caching, etc.
│   └── main.py           # FastAPI application factory
├── data/                 # Downloads, intermediate data, generated tiles
├── data_pipeline/        # Tile generation pipeline & tile server
│   └── servers/tile_server.py
├── dev_server.py         # Convenience launcher for the API service
├── requirements*.txt     # Dependency sets
├── scripts/              # Deployment and maintenance scripts
├── tests/                # Pytest suites
└── Dockerfile            # Production container build
```

---

## 3. Prerequisites

- macOS / Linux / WSL with Python 3.11+
- GDAL and geospatial dependencies (installed automatically when using the provided Dockerfile; locally ensure GDAL headers are available)
- Optional: Redis (some health checks expect connectivity, but the mock setup runs without it)

---

## 4. Local Environment Setup

```bash
# 1. Clone and enter repository
cd CLISApp/current_semester/IFN735_25se2_Industry_Project/CLISAPP/CLISApp-backend

# 2. Create virtualenv
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env to suit your machine (ports, paths, API keys)
```

Important variables (see `.env.example`):
- `DEBUG`, `LOG_LEVEL`
- `PORT`, `HOST`
- `DATA_ROOT`, `TILES_PATH`, `DOWNLOADS_PATH`, `PROCESSING_PATH`
- **NASA Earthdata credentials (Required for MODIS):**
  - `NASA_USERNAME` - Your NASA Earthdata username
  - `NASA_PASSWORD` - Your NASA Earthdata password
  - Register at: https://urs.earthdata.nasa.gov/users/new
- Optional API credentials for Copernicus downloads

Data directories (`data/downloads`, `data/processing`, `data/tiles`) are created automatically by the settings class, but ensure they exist if you run outside the Python settings module.

### 4.1 NASA Earthdata Setup (MODIS Data)

**Temperature and humidity data now use MODIS LANCE** (near real-time satellite observations) instead of CAMS forecasts. You need NASA Earthdata credentials:

1. **Register**: Visit https://urs.earthdata.nasa.gov/users/new
2. **Get credentials**: After registration, use your username/password
3. **Configure**: Add to `.env`:
   ```bash
   NASA_USERNAME=your_username
   NASA_PASSWORD=your_password
   ```

**Data Source Comparison:**

| Layer | Old Source | New Source | Resolution | Latency |
|-------|-----------|------------|------------|---------|
| Temperature | CAMS Forecast | MODIS LANCE (MOD07/MYD07) | 5km (was 40km) | 3-5 hours (was 5 days) |
| Humidity | CAMS Forecast | MODIS LANCE (MOD07/MYD07) | 5km (was 40km) | 3-5 hours (was 5 days) |
| Precipitation | GPM IMERG | GPM IMERG (unchanged) | 10km | 4-6 hours |
| PM2.5 | QLD Gov Real-time | QLD Gov Real-time (unchanged) | Station data | Real-time |
| UV Index | CAMS Forecast | CAMS Forecast (unchanged) | 40km | 5 days |

**MODIS Satellites:**
- Terra (MOD07): ~2 passes/day over Queensland
- Aqua (MYD07): ~2 passes/day over Queensland
- **Total**: ~4 observations/day with cloud gap filling

---

## 5. Running Services & Pipelines (No Docker)

### 5.1 Region API Service (FastAPI)

`app/main.py` exposes the REST API. Use `dev_server.py` (hot-reload) or `uvicorn` directly.

```bash
# Activate venv first
source venv/bin/activate

# Option A: convenience script (reload enabled, reads settings)
python dev_server.py

# Option B: manual uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Key endpoints once running at `http://localhost:8080`:
- `GET /api/v1/health`
- `GET /api/v1/regions/search?q=Sunny&limit=5`
- `GET /docs` for Swagger UI

### 5.2 Tile Server

`data_pipeline/servers/tile_server.py` serves tiles and demo pages.

```bash
source venv/bin/activate
python data_pipeline/servers/tile_server.py  # Defaults to host 0.0.0.0, port 8000
```

Useful endpoints at `http://localhost:8000`:
- `GET /health` – health status & tile statistics
- `GET /tiles/pm25/8/241/155.png` – sample tile
- `GET /tiles/pm25/demo` – HTML preview

> **Tip:** Run both services in separate terminals. The frontend expects the API on `:8080` and the tile server on `:8000` (adjust `src/constants/apiEndpoints.ts` if you prefer a different layout).

### 5.3 Data Pipeline Runners

`data_pipeline/pipeline_scripts/` provides five one-click scripts covering **PM2.5 / Precipitation / Temperature / Humidity / UV** with "download → process → generate tiles" workflow.

**Prerequisites:**
- NASA Earthdata credentials in `.env` (Required for temperature/humidity)
- Optional: Copernicus CDS credentials in `.cdsapirc` (for PM2.5/UV)
- System dependencies: `eccodes` (macOS: `brew install eccodes`)

**Running pipelines** (activate venv first):

```bash
source venv/bin/activate

# PM2.5 (CAMS GRIB → GeoTIFF → Tiles)
python -m data_pipeline.pipeline_scripts.run_pipeline_pm25

# Precipitation (GPM IMERG daily, can switch modes with parameters)
python -m data_pipeline.pipeline_scripts.run_pipeline_precip

# Temperature (MODIS LANCE - Near Real-Time Satellite)
# Downloads MOD07/MYD07, processes temperature profiles, creates composite, generates tiles
python -m data_pipeline.pipeline_scripts.run_pipeline_temp

# Humidity (MODIS LANCE - Total Column Water Vapor)
# Downloads MOD07/MYD07, extracts water vapor, creates composite, generates tiles
python -m data_pipeline.pipeline_scripts.run_pipeline_humidity

# UV Index (CAMS biologically effective dose)
python -m data_pipeline.pipeline_scripts.run_pipeline_uv
```

**Generated tiles** can be found in `tiles/<layer>/`. For batch processing multiple layers, call these scripts in sequence or create a wrapper script.

### 5.4 MODIS Pipeline Details (Temperature/Humidity)

**Temperature Pipeline (`run_pipeline_temp.py`):**
1. Downloads MOD07/MYD07 HDF files from LANCE (last 48 hours)
2. Extracts 2m air temperature from atmospheric profiles
3. Converts swath data to regular grid (Queensland subset)
4. Creates temporal composite (24-hour window) to fill cloud gaps
5. Generates PNG tiles (zoom levels 6-12)

**Humidity Pipeline (`run_pipeline_humidity.py`):**
1. Downloads MOD07/MYD07 HDF files from LANCE (last 48 hours)
2. Extracts total precipitable water vapor
3. Converts swath data to regular grid (Queensland subset)
4. Creates temporal composite (24-hour window) to fill cloud gaps
5. Generates PNG tiles (zoom levels 6-12)

**Cloud Gap Filling:**
- Uses 24-48 hour temporal window
- Combines Terra + Aqua observations (~4 passes/day)
- Prefers most recent clear observation
- Generates quality layer (observation count per pixel)

**Performance:**
- Typical runtime: 15-25 minutes per layer
- Download: ~50-200 MB per 48-hour window
- Composite coverage: 85-95% (Queensland)

**Troubleshooting MODIS Pipelines:**
```bash
# Test NASA authentication
cd CLISApp-backend
python -m data_pipeline.downloads.modis_lance.auth

# Test full MODIS fetch workflow
python tests/modis/test_modis_fetch.py

# Manual temperature processing
python data_pipeline/processing/temp/process_modis_temp_to_tif.py --hours-back 48

# Check downloaded files
python -m data_pipeline.downloads.modis_lance.fetch_mod07 --stats
```

---

## 6. Troubleshooting

| Symptom | Possible Cause | Fix |
| --- | --- | --- |
| `curl http://localhost:8080/api/v1/health` fails | API service not running / wrong port | Re-run `python dev_server.py`; confirm `.env` port |
| Tile requests return 404 | Tiles missing for requested layer/zoom | Verify `data/tiles/<layer>/<level>/<z>/<x>/<y>.png`; regenerate via API or pipeline |
| Frontend 404 on `/api/v1/...` | Frontend `BASE_URL` still set to tile server port | Edit `src/constants/apiEndpoints.ts` (development should point to `http://localhost:8080`) |
| Docker build fails on GDAL/Fiona | Using old base image | Ensure Dockerfile uses `python:3.11-slim-bookworm` |
| Large downloads from CDS/NASA fail | Credentials missing | Populate `.env` with valid keys | 

---

## 7. References & Next Steps

- API documentation: `http://localhost:8080/docs`
- Tile server demo: `http://localhost:8000/tiles/pm25/demo`
- Data pipeline scripts: `data_pipeline/`
- Frontend integration guide: see `CLISApp-frontend/README.md`

For production deployment, follow the Docker workflow, configure HTTPS, and connect to a managed Redis/Postgres instance if required.
