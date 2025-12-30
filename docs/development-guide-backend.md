# Development Guide (Backend)

## Prerequisites

- Python 3.11+ (see backend README)
- System geospatial deps may be required for rasterio/GDAL depending on platform

## Setup

```bash
cd CLISApp-backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cp .env.example .env
# edit .env (ports, paths, credentials)
```

## Run (Local)

### Option A: start both services

```bash
./start.sh
# or
python start_all_services.py
```

This starts:

- API service on `:8080`
- Tile server on `:8000`

### Option B: run separately

API service:

```bash
python dev_server.py
# or
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Tile server:

```bash
python data_pipeline/servers/tile_server.py
# or
uvicorn data_pipeline.servers.tile_server:app --host 0.0.0.0 --port 8000
```

## Test

```bash
pytest
```

## Useful Endpoints

- API docs: `http://localhost:8080/docs` (debug)
- Tile demo: `http://localhost:8000/tiles/pm25/demo`

## Data + Credentials Notes

- NASA Earthdata credentials are required for some pipelines (see backend README).
- Tiles and data directories are expected under `CLISApp-backend/data/` and `CLISApp-backend/tiles/`.
