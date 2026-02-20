import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.io import MemoryFile

from data_pipeline.processing.common.generate_tiles import PM25TileGenerator


def _make_in_memory_dataset(width=10, height=10, bounds=(-180.0, -85.0, 180.0, 85.0)):
    data = np.arange(width * height, dtype=np.float32).reshape((height, width))
    transform = from_bounds(*bounds, width, height)

    memfile = MemoryFile()
    with memfile.open(
        driver="GTiff",
        height=height,
        width=width,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dataset:
        dataset.write(data, 1)

    return memfile


def test_extract_tile_data_includes_buffer():
    buffer_pixels = 4
    generator = PM25TileGenerator("dummy.tif", buffer_pixels=buffer_pixels)

    memfile = _make_in_memory_dataset()
    with memfile.open() as src:
        data = generator._extract_tile_data(src, zoom=0, x=0, y=0)

    assert data is not None
    assert data.shape == (256 + 2 * buffer_pixels, 256 + 2 * buffer_pixels)


def test_fill_missing_with_neighbor_mean_multiple_passes():
    generator = PM25TileGenerator("dummy.tif", fill_passes=3)
    data = np.ones((5, 5), dtype=np.float32)
    data[1:4, 1:4] = 0.0

    filled = generator.fill_missing_with_neighbor_mean(data)

    assert np.all(filled != 0.0)


def test_extract_tile_data_handles_subpixel_window():
    buffer_pixels = 4
    generator = PM25TileGenerator("dummy.tif", buffer_pixels=buffer_pixels)

    memfile = _make_in_memory_dataset(
        width=37,
        height=44,
        bounds=(138.0, -29.0, 154.0, -10.0),
    )
    with memfile.open() as src:
        x, y = generator.deg2num(-20.0, 146.0, 11)
        data = generator._extract_tile_data(src, zoom=11, x=x, y=y)

    assert data is not None
    assert data.shape == (256 + 2 * buffer_pixels, 256 + 2 * buffer_pixels)
