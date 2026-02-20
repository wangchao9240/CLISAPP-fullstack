import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.io import MemoryFile
from PIL import Image
from unittest.mock import MagicMock

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


def test_compute_native_max_zoom():
    generator = PM25TileGenerator("dummy.tif")
    coarse_zoom = generator._compute_native_max_zoom(0.45)
    fine_zoom = generator._compute_native_max_zoom(0.1)

    assert coarse_zoom in {9, 10}
    assert fine_zoom in {11, 12}


def test_upsample_zoom_level(tmp_path):
    output_dir = tmp_path / "tiles"
    parent_dir = output_dir / "pm25" / "10" / "0"
    parent_dir.mkdir(parents=True, exist_ok=True)
    parent_tile = parent_dir / "0.png"
    Image.new("RGBA", (256, 256), (255, 0, 0, 255)).save(parent_tile)

    generator = PM25TileGenerator("dummy.tif", output_dir=output_dir, layer_name="pm25")
    count = generator._upsample_zoom_level(11)

    assert count == 4
    child_dir = output_dir / "pm25" / "11"
    expected_tiles = [
        child_dir / "0" / "0.png",
        child_dir / "1" / "0.png",
        child_dir / "0" / "1.png",
        child_dir / "1" / "1.png",
    ]
    for tile in expected_tiles:
        assert tile.exists()
        with Image.open(tile) as img:
            assert img.size == (256, 256)


def test_generate_all_tiles_uses_upsample_for_high_zoom(tmp_path):
    tiff_path = tmp_path / "test.tif"
    data = np.ones((10, 10), dtype=np.float32)
    transform = from_bounds(0.0, 0.0, 1.0, 1.0, 10, 10)

    with rasterio.open(
        tiff_path,
        "w",
        driver="GTiff",
        height=10,
        width=10,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
    ) as dataset:
        dataset.write(data, 1)

    generator = PM25TileGenerator(
        str(tiff_path),
        output_dir=tmp_path / "tiles",
        layer_name="pm25",
        zoom_levels=[10, 11, 12],
    )
    generator.generate_tiles_for_zoom = MagicMock(return_value=1)
    generator._upsample_zoom_level = MagicMock(return_value=1)

    generator.generate_all_tiles()

    assert generator.generate_tiles_for_zoom.call_args_list == [((10,),), ((11,),)]
    generator._upsample_zoom_level.assert_called_once_with(12)
