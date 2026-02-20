# TIF Pre-Interpolation Design

**Goal:** Reduce visible banding artifacts in climate layer tiles by pre-interpolating low-resolution GeoTIFFs before tile generation.

**Architecture:** Add a preprocessing step in `PM25TileGenerator.generate_all_tiles()` that detects low-resolution TIFs (width/height < 256), upsamples them using `rasterio.warp.reproject` with bilinear resampling, and generates tiles from the upsampled temporary GeoTIFF. The original TIF path is restored after tile generation, and the temporary file is cleaned up.

**Tech Stack:** Python, rasterio, numpy, tempfile.

---

## Data Flow
1. Open the source TIF, compute `native_max_zoom`.
2. If the source TIF is low-res, upsample it to a temporary TIF using bilinear resampling.
3. Temporarily switch `self.geotiff_file` to the temp TIF.
4. Generate tiles for all requested zoom levels.
5. Restore original `self.geotiff_file` and delete the temp TIF.

## Error Handling
- If upsampling is skipped (already high-res), proceed normally.
- If temp file cleanup fails, swallow the exception to avoid breaking pipeline execution.
- Preserve nodata handling during reproject.

## Testing
- Unit test for `_create_upsampled_tif()` to validate scaling, bounds, and clamped values.
- Unit test to ensure high-res inputs skip upsampling.
- Unit test to confirm `generate_all_tiles()` swaps and restores `geotiff_file`.
