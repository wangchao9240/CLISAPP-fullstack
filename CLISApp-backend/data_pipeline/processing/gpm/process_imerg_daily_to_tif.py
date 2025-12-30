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
    if lon_values.max() > 180.0:
        return ((lon_values + 180.0) % 360.0) - 180.0
    return lon_values


def _pick_var(ds: xr.Dataset, candidates: list[str]) -> str:
    for name in candidates:
        if name in ds.data_vars:
            return name
    raise KeyError(f"None of variables {candidates} found in dataset: {list(ds.data_vars)}")


def main():
    raw_dir = Path("data_pipeline/data/raw/gpm/imerg_daily")
    out_dir = Path("data_pipeline/data/processed/gpm")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pick latest file in YYYYMMDD subfolders or root
    candidates = list(raw_dir.rglob("*.nc4")) + list(raw_dir.rglob("*.nc"))
    if not candidates:
        raise SystemExit(f"No IMERG daily files found under {raw_dir}")

    src = max(candidates, key=lambda p: p.stat().st_mtime)
    ds = xr.open_dataset(src)

    lon_name = "lon" if "lon" in ds.coords else ("longitude" if "longitude" in ds.coords else None)
    lat_name = "lat" if "lat" in ds.coords else ("latitude" if "latitude" in ds.coords else None)
    if lon_name is None or lat_name is None:
        raise SystemExit("Could not find lon/lat coordinates in dataset")

    var_name = _pick_var(ds, ["precipitationCal", "precipitation", "precipitationUncal"])
    da = ds[var_name]

    # IMERG daily usually is already daily; squeeze any leftover dims
    if "time" in da.dims:
        da = da.mean(dim="time", skipna=True)

    lons = da[lon_name].values.astype(float)
    lats = da[lat_name].values.astype(float)
    lons_norm = _normalize_lon(lons)
    if not np.allclose(lons, lons_norm):
        da = da.assign_coords({lon_name: (da[lon_name].dims, lons_norm)})
        lons = lons_norm

    # Ensure coordinates are monotonically increasing for slicing
    da = da.sortby(lon_name)
    da = da.sortby(lat_name)

    lon_min = QLD_BOUNDS["min_lon"]; lon_max = QLD_BOUNDS["max_lon"]
    lat_min = QLD_BOUNDS["min_lat"]; lat_max = QLD_BOUNDS["max_lat"]
    da_qld = da.sel({
        lon_name: slice(lon_min, lon_max),
        lat_name: slice(lat_min, lat_max),
    })

    data2d = np.squeeze(da_qld.values).astype("float32")
    data2d = np.nan_to_num(data2d, nan=0.0)

    lons_sub = da_qld[lon_name].values.astype(float)
    lats_sub = da_qld[lat_name].values.astype(float)
    transform = from_bounds(lons_sub.min(), lats_sub.min(), lons_sub.max(), lats_sub.max(), data2d.shape[1], data2d.shape[0])

    tif_path = out_dir / "imerg_daily_precip_qld.tif"
    with rasterio.open(
        tif_path, "w", driver="GTiff", height=data2d.shape[0], width=data2d.shape[1], count=1,
        dtype="float32", crs="EPSG:4326", transform=transform, compress="lzw"
    ) as dst:
        if lats_sub[0] < lats_sub[-1]:
            dst.write(np.flipud(data2d), 1)
        else:
            dst.write(data2d, 1)

    print(f"Saved: {tif_path}")


if __name__ == "__main__":
    main()


