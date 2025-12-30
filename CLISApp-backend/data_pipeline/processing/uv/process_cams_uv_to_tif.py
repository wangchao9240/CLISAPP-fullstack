import os
from pathlib import Path

import numpy as np
import xarray as xr
import rasterio
from rasterio.transform import from_bounds


QLD_BOUNDS = {
    "min_lon": 137.0,
    "max_lon": 154.0,
    "min_lat": -29.5,
    "max_lat": -9.0,
}


def _normalize_lon(lon_values: np.ndarray) -> np.ndarray:
    """Ensure longitudes are in [-180, 180] range for easy subsetting."""
    if lon_values.max() > 180.0:
        # Convert [0, 360] -> [-180, 180]
        return ((lon_values + 180.0) % 360.0) - 180.0
    return lon_values


def _pick_var(ds: xr.Dataset, candidates: list[str]) -> str:
    for name in candidates:
        if name in ds.data_vars:
            return name
    raise KeyError(f"None of variables {candidates} found in dataset: {list(ds.data_vars)}")


def _pick_coord(ds: xr.Dataset, candidates: list[str]) -> str:
    for name in candidates:
        if name in ds.coords:
            return name
    # Some datasets expose as data_vars
    for name in candidates:
        if name in ds:
            return name
    raise KeyError(f"None of coords {candidates} found in dataset: {list(ds.coords)}")


def main():
    raw_dir = Path("data_pipeline/data/raw/cams/uv")
    out_dir = Path("data_pipeline/data/processed/uv")
    out_dir.mkdir(parents=True, exist_ok=True)

    nc_files = sorted(raw_dir.glob("*.nc"))
    if not nc_files:
        raise SystemExit(f"No UV NetCDF files found in {raw_dir}")
    src_path = max(nc_files, key=lambda p: p.stat().st_mtime)
    print(f"Using latest UV NetCDF: {src_path.name}")

    ds = xr.open_dataset(src_path)

    lon_name = _pick_coord(ds, ["longitude", "lon"]) 
    lat_name = _pick_coord(ds, ["latitude", "lat"]) 
    time_name = _pick_coord(ds, ["time"]) if "time" in ds.dims or "time" in ds.coords else None

    var_name = _pick_var(ds, ["uv_biologically_effective_dose", "uvbed", "uv_index", "uvi"])  # broad fallbacks
    uv = ds[var_name]

    # Reduce any non-spatial dims (e.g., time, leadtime/step) by max to get a 2D field
    non_spatial_dims = [d for d in uv.dims if d not in {lon_name, lat_name}]
    uv2 = uv.max(dim=non_spatial_dims, skipna=True) if non_spatial_dims else uv

    # Normalize and subset longitudes
    lons = uv2[lon_name].values.astype(float)
    lats = uv2[lat_name].values.astype(float)
    lons_norm = _normalize_lon(lons)

    # If normalization changed longitudes, reassign
    if not np.allclose(lons, lons_norm):
        uv2 = uv2.assign_coords({lon_name: (uv2[lon_name].dims, lons_norm)})
        lons = lons_norm

    # Subset to Queensland bounds
    lon_min = QLD_BOUNDS["min_lon"]
    lon_max = QLD_BOUNDS["max_lon"]
    lat_min = QLD_BOUNDS["min_lat"]
    lat_max = QLD_BOUNDS["max_lat"]

    uv_qld = uv2.sel({
        lon_name: slice(lon_min, lon_max) if lons[0] < lons[-1] else slice(lon_max, lon_min),
        lat_name: slice(lat_min, lat_max) if lats[0] < lats[-1] else slice(lat_max, lat_min),
    })

    # Prepare GeoTIFF export
    lons_sub = uv_qld[lon_name].values.astype(float)
    lats_sub = uv_qld[lat_name].values.astype(float)
    data = uv_qld.values

    # Ensure 2D array
    data2d = np.squeeze(data)
    if data2d.ndim != 2:
        raise ValueError(f"Expected 2D array after squeeze, got shape {data2d.shape}")

    data2d = np.nan_to_num(data2d, nan=0.0).astype("float32")

    transform = from_bounds(lons_sub.min(), lats_sub.min(), lons_sub.max(), lats_sub.max(), data2d.shape[1], data2d.shape[0])

    tif_path = out_dir / "cams_uv_qld.tif"
    with rasterio.open(
        tif_path,
        "w",
        driver="GTiff",
        height=data2d.shape[0],
        width=data2d.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        compress="lzw",
    ) as dst:
        # If latitude ascending, flip to match geotransform (north-up)
        if lats_sub[0] < lats_sub[-1]:
            dst.write(np.flipud(data2d), 1)
        else:
            dst.write(data2d, 1)

    print(f"Saved: {tif_path}")


if __name__ == "__main__":
    main()


