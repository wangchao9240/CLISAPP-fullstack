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

### Recommended: Use Makefile (from repo root)

```bash
# Start all services
make up

# Or start individually
make api-up     # API service only
make tiles-up   # Tile server only

# Check status
make status

# View logs
make logs

# Stop services
make down
```

This starts:

- API service on `:8080` - `/api/v1/*` endpoints
- Tile server on `:8000` - `/tiles/*` tile images

### Advanced: Direct uvicorn (optional)

For advanced use cases, you can run uvicorn directly:

API service:

```bash
cd CLISApp-backend
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

Tile server:

```bash
cd CLISApp-backend
uvicorn data_pipeline.servers.tile_server:app --host 0.0.0.0 --port 8000
```

**Note:** The backend-local scripts (`start.sh`, `start_all_services.py`, `dev_server.py`) are deprecated and will be removed in Phase 2.

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
