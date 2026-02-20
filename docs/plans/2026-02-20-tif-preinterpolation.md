# TIF Pre-Interpolation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a pre-interpolation step that upsamples low-resolution GeoTIFFs before tile generation to reduce visible banding artifacts.

**Architecture:** Introduce `_create_upsampled_tif()` in `PM25TileGenerator` to resample the source TIF via `rasterio.reproject` and swap `self.geotiff_file` during `generate_all_tiles()`, restoring and cleaning up afterward.

**Tech Stack:** Python, rasterio, numpy, tempfile, pytest.

---

### Task 1: Add tests for upsampled TIF behavior

**Files:**
- Modify: `CLISApp-backend/tests/test_generate_tiles_buffer.py`

**Step 1: Write the failing tests**

```python
def test_create_upsampled_tif(tmp_path):
    ...

def test_create_upsampled_tif_skips_highres(tmp_path):
    ...

def test_generate_all_tiles_uses_upsampled_tif(tmp_path, monkeypatch):
    ...
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. ./venv/bin/python -m pytest tests/test_generate_tiles_buffer.py::test_create_upsampled_tif -v`  
Expected: FAIL with `AttributeError: '_create_upsampled_tif'` or missing behavior.

**Step 3: Commit**

```bash
git add CLISApp-backend/tests/test_generate_tiles_buffer.py
git commit -m "test: cover tif pre-interpolation"
```

---

### Task 2: Implement `_create_upsampled_tif()` and import

**Files:**
- Modify: `CLISApp-backend/data_pipeline/processing/common/generate_tiles.py`

**Step 1: Add import**

```python
import tempfile
```

**Step 2: Add `_create_upsampled_tif()` implementation**

```python
def _create_upsampled_tif(self, scale_factor: int = 8) -> Optional[str]:
    ...
```

**Step 3: Run tests**

Run: `PYTHONPATH=. ./venv/bin/python -m pytest tests/test_generate_tiles_buffer.py::test_create_upsampled_tif -v`  
Expected: PASS.

**Step 4: Commit**

```bash
git add CLISApp-backend/data_pipeline/processing/common/generate_tiles.py
git commit -m "feat: add tif pre-interpolation helper"
```

---

### Task 3: Integrate pre-interpolation into `generate_all_tiles()`

**Files:**
- Modify: `CLISApp-backend/data_pipeline/processing/common/generate_tiles.py:~460`

**Step 1: Swap `self.geotiff_file` before tile generation**

```python
upsampled_tif = self._create_upsampled_tif(scale_factor=8)
original_geotiff = self.geotiff_file
if upsampled_tif is not None:
    self.geotiff_file = upsampled_tif
```

**Step 2: Restore original and cleanup before return**

```python
if upsampled_tif is not None:
    self.geotiff_file = original_geotiff
    try:
        os.remove(upsampled_tif)
    except OSError:
        pass
```

**Step 3: Run full test file**

Run: `PYTHONPATH=. ./venv/bin/python -m pytest tests/test_generate_tiles_buffer.py -v`  
Expected: PASS.

**Step 4: Commit**

```bash
git add CLISApp-backend/data_pipeline/processing/common/generate_tiles.py
git commit -m "feat: pre-interpolate low-res tifs before tiling"
```
