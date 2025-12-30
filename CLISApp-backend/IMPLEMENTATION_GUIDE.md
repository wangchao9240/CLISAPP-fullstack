# CLISApp 实时气候数据系统 - 实施指南

## 📋 项目概览

**项目名称**: CLISApp Backend - 实时气候数据获取与渲染系统
**目标**: 将预测数据（CAMS/GPM）替换为实时免费API数据
**覆盖范围**: 昆士兰州全境
**数据维度**: 5个（温度、湿度、降水、UV指数、PM2.5）

---

## ✅ 当前进度：第一步已完成（2024-11-20）

### 已实现功能

#### 1. 昆士兰州网格配置系统
**文件**: `data_pipeline/config/grid_config.py`

```python
# 网格参数
总采样点: 1,628个
网格精度: 50km (0.45°)
覆盖范围:
  - 北: -10.0° (Cape York)
  - 南: -29.0° (NSW边界)
  - 东: 154.0° (太平洋海岸)
  - 西: 138.0° (SA/NT边界)
```

**核心函数**:
- `generate_grid_points()` - 生成网格采样点
- `get_grid_dimensions()` - 获取网格维度
- `GRID_POINTS` - 预生成的1,628个采样点列表

#### 2. Open-Meteo 实时数据获取器
**文件**: `data_pipeline/downloads/openmeteo/fetch_realtime.py`

**功能**:
- ✅ 批量异步获取（100点/批次）
- ✅ 支持4个气候维度（温度、湿度、降水、UV）
- ✅ 自动错误处理和重试
- ✅ Redis缓存接口
- ✅ 优雅降级（空气质量数据不可用时继续）

**关键类**:
```python
class OpenMeteoFetcher:
    async def fetch_all_data(grid_points) -> Dict
    async def fetch_and_cache(grid_points, ttl) -> Dict
    def cache_to_redis(data, ttl) -> None
```

#### 3. 测试验证
**文件**: `test_openmeteo_fetch.py`, `test_uv_check.py`, `test_api_weighting.py`

**验证结果**:
- ✅ 网格配置正确（1,628点）
- ✅ API批量获取成功
- ✅ 数据质量验证通过
- ✅ UV指数日夜变化正常（0→9.4峰值）
- ✅ API加权测试完成（100点≈4x加权）

---

## 📊 数据获取现状

### 成功获取的维度（4/5）

| 维度 | 数据源 | API端点 | 状态 | 更新频率 |
|------|--------|---------|------|----------|
| **温度** | Open-Meteo | `/v1/forecast` | ✅ 可用 | 每10分钟 |
| **湿度** | Open-Meteo | `/v1/forecast` | ✅ 可用 | 每10分钟 |
| **降水** | Open-Meteo | `/v1/forecast` | ✅ 可用 | 每10分钟 |
| **UV指数** | Open-Meteo | `/v1/forecast` | ✅ 可用 | 每10分钟 |
| **PM2.5** | ~~Open-Meteo~~ | ~~`/v1/air-quality`~~ | ❌ 不可用 | N/A |

### PM2.5 问题说明

**问题**: Open-Meteo Air Quality API 对澳大利亚返回 404
**原因**: 数据覆盖范围仅限欧洲和北美
**影响**: 当前仅4个维度可用（80%功能）

**解决方案（待实施）**:
- 选项1: 集成WAQI API获取主要城市PM2.5（免费）
- 选项2: 暂时不包含PM2.5图层
- **推荐**: 先完成4维度系统，稍后添加PM2.5

---

## 🔢 API限制与使用量分析

### Open-Meteo 免费额度

```yaml
限制:
  每分钟: 600 次调用
  每小时: 5,000 次调用
  每天: 10,000 次调用

计费方式: 加权计算
  - 单点请求: 1x
  - 批量请求: 根据数据量加权
  - 100点 × 4维度（current）: ~4x加权
```

### 我们的实际使用量

```
单次完整更新（1,628点）:
  批次数: 17批（每批100点）
  每批加权: ~4x
  总计: 17 × 4 = 68 加权调用

每10分钟更新:
  每小时: 6 × 68 = 408 调用  (8% of 5,000)  ✅
  每天: 144 × 68 = 9,792 调用  (98% of 10,000)  ✅

安全余量: 208 调用/天 (2%)  ✅
```

**结论**: ✅ 完全在免费额度内，可以支持每10分钟更新

**⚠️ 重要限制**:
- **不要添加 hourly 参数**（会增加加权到10-50x）
- **只获取 current 值**即可满足需求

---

## 🏗️ 系统架构

### 完整数据流

```
┌─────────────────────────────────────────────────────────┐
│  Step 1: 数据获取 (Data Fetching) - ✅ 已完成           │
├─────────────────────────────────────────────────────────┤
│  • Open-Meteo API                                       │
│  • 1,628个网格点 × 4个维度                              │
│  • 每10分钟批量获取（17次API调用）                       │
│  输出: JSON格式的点数据                                  │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Step 2: 数据存储 (Caching) - ⏳ 待实施                 │
├─────────────────────────────────────────────────────────┤
│  • Redis缓存（最新数据，1小时TTL）                       │
│  • PostgreSQL存档（历史数据，可选）                      │
│  输出: 缓存的点数据                                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Step 3: 插值处理 (Interpolation) - ⏳ 待实施           │
├─────────────────────────────────────────────────────────┤
│  • 从1,628个点插值到高分辨率栅格（5km精度）              │
│  • 使用scipy.interpolate.griddata                       │
│  • 每个图层生成一个GeoTIFF文件                           │
│  输出: processed/{layer}_realtime.tif                   │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Step 4: 瓦片生成 (Tile Generation) - ⏳ 待实施         │
├─────────────────────────────────────────────────────────┤
│  • 复用现有generate_tiles.py                            │
│  • GeoTIFF → PNG瓦片（XYZ格式）                         │
│  • Zoom levels: 6-12                                    │
│  • 增量更新（只更新变化的瓦片）                          │
│  输出: tiles/{layer}/{z}/{x}/{y}.png                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Step 5: 定时调度 (Scheduling) - ⏳ 待实施              │
├─────────────────────────────────────────────────────────┤
│  • Celery Beat定时任务                                  │
│  • 每10分钟执行完整更新流程                              │
│  • 监控和错误通知                                        │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Step 6: API服务 (Existing) - ✅ 已存在                │
├─────────────────────────────────────────────────────────┤
│  • FastAPI (Port 8080): 区域查询API                     │
│  • Tile Server (Port 8000): 瓦片服务                    │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  Frontend: React Native Mobile App - ✅ 已存在          │
└─────────────────────────────────────────────────────────┘
```

---

## 🗂️ 文件结构

```
CLISApp-backend/
├── data_pipeline/
│   ├── config/
│   │   ├── __init__.py
│   │   └── grid_config.py                    ✅ 新建 - 网格配置
│   │
│   ├── downloads/
│   │   ├── openmeteo/
│   │   │   ├── __init__.py
│   │   │   └── fetch_realtime.py             ✅ 新建 - 数据获取器
│   │   ├── pm25/download_pm25.py             (现有-CAMS)
│   │   └── gpm/download_gpm_imerg.py         (现有-NASA)
│   │
│   ├── processing/
│   │   ├── common/
│   │   │   ├── generate_tiles.py             (现有-复用)
│   │   │   └── interpolate_to_raster.py      ⏳ 待创建
│   │   └── realtime/
│   │       └── process_realtime_data.py      ⏳ 待创建
│   │
│   ├── scheduler/
│   │   ├── __init__.py                       ⏳ 待创建
│   │   ├── update_climate_data.py            ⏳ 待创建
│   │   └── celery_config.py                  ⏳ 待创建
│   │
│   └── servers/
│       └── tile_server.py                     (现有)
│
├── app/
│   ├── main.py                                (现有-FastAPI)
│   ├── services/
│   │   └── climate_data_service.py            (现有-需更新)
│   └── api/
│       └── v1/regions.py                      (现有)
│
├── tests/
│   ├── test_openmeteo_fetch.py               ✅ 新建
│   ├── test_uv_check.py                      ✅ 新建
│   └── test_api_weighting.py                 ✅ 新建
│
├── requirements.txt                           ✅ 已更新
├── docker-compose.yml                         ⏳ 待更新
├── Dockerfile                                 (现有)
└── IMPLEMENTATION_GUIDE.md                    ✅ 本文档
```

---

## 📝 详细实施步骤

### 第一步：数据获取 ✅ 已完成

**状态**: 100% 完成
**耗时**: 约4小时
**文件**:
- `data_pipeline/config/grid_config.py`
- `data_pipeline/downloads/openmeteo/fetch_realtime.py`
- 测试脚本 × 3

**验证**:
```bash
# 测试网格配置
python -m data_pipeline.config.grid_config

# 测试数据获取
python test_openmeteo_fetch.py --num-points 10

# 测试UV变化
python test_uv_check.py

# 测试API加权
python test_api_weighting.py
```

---

### 第二步：Redis缓存层 ⏳ 下一步

**目标**: 实现数据缓存机制，加速查询和减少重复计算

**估计耗时**: 1-2小时

#### 实施详情

**1. 创建Redis缓存工具类**

文件: `data_pipeline/utils/redis_cache.py`

```python
"""
Redis缓存管理工具
"""
import redis
import json
from typing import Optional, Dict, List
from datetime import datetime, timedelta

class ClimateDataCache:
    """气候数据Redis缓存"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    def cache_point_data(self, key: str, data: Dict, ttl: int = 3600):
        """缓存单个点的数据"""
        self.redis.setex(key, ttl, json.dumps(data))

    def get_point_data(self, key: str) -> Optional[Dict]:
        """获取缓存的点数据"""
        data = self.redis.get(key)
        return json.loads(data) if data else None

    def cache_all_points(self, points_data: Dict[str, Dict], ttl: int = 3600):
        """批量缓存所有点数据"""
        pipe = self.redis.pipeline()
        for key, data in points_data.items():
            cache_key = f"climate:current:{key}"
            pipe.setex(cache_key, ttl, json.dumps(data))
        pipe.set("climate:last_update", datetime.utcnow().isoformat())
        pipe.execute()

    def get_all_points(self) -> Dict[str, Dict]:
        """获取所有缓存的点数据"""
        keys = self.redis.keys("climate:current:*")
        if not keys:
            return {}

        pipe = self.redis.pipeline()
        for key in keys:
            pipe.get(key)

        results = {}
        for key, data in zip(keys, pipe.execute()):
            if data:
                coord_key = key.replace("climate:current:", "")
                results[coord_key] = json.loads(data)

        return results

    def get_last_update(self) -> Optional[str]:
        """获取最后更新时间"""
        return self.redis.get("climate:last_update")

    def clear_cache(self):
        """清空所有缓存"""
        keys = self.redis.keys("climate:*")
        if keys:
            self.redis.delete(*keys)
```

**2. 更新数据获取器集成Redis**

修改: `data_pipeline/downloads/openmeteo/fetch_realtime.py`

```python
# 在 OpenMeteoFetcher 类中添加:
from data_pipeline.utils.redis_cache import ClimateDataCache

class OpenMeteoFetcher:
    def __init__(self, cache: Optional[ClimateDataCache] = None):
        self.cache = cache

    async def fetch_and_cache(self, grid_points: List[Dict]) -> Dict:
        """获取数据并自动缓存"""
        data = await self.fetch_all_data(grid_points)

        if self.cache:
            self.cache.cache_all_points(data, ttl=3600)

        return data
```

**3. 测试脚本**

文件: `tests/test_redis_cache.py`

```python
import asyncio
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher
from data_pipeline.utils.redis_cache import ClimateDataCache
from data_pipeline.config.grid_config import GRID_POINTS

async def test_cache():
    # 初始化缓存
    cache = ClimateDataCache()
    cache.clear_cache()

    # 获取并缓存数据
    fetcher = OpenMeteoFetcher(cache=cache)
    data = await fetcher.fetch_and_cache(GRID_POINTS[:10])

    print(f"Cached {len(data)} points")

    # 验证缓存
    cached_data = cache.get_all_points()
    print(f"Retrieved {len(cached_data)} points from cache")

    # 检查更新时间
    last_update = cache.get_last_update()
    print(f"Last update: {last_update}")

asyncio.run(test_cache())
```

**验收标准**:
- ✅ 数据成功写入Redis
- ✅ 可以从Redis读取数据
- ✅ TTL正确设置
- ✅ 最后更新时间正确记录

---

### 第三步：插值生成栅格 ⏳ 待实施

**目标**: 将稀疏的点数据插值为连续的高分辨率栅格

**估计耗时**: 2-3小时

#### 实施详情

**1. 创建插值器**

文件: `data_pipeline/processing/common/interpolate_to_raster.py`

```python
"""
从点数据插值生成GeoTIFF栅格
"""
import numpy as np
from scipy.interpolate import griddata
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from pathlib import Path
from typing import Dict, List, Tuple

class RasterInterpolator:
    """栅格插值器"""

    def __init__(self, bounds: Dict, resolution_km: float = 5):
        """
        Args:
            bounds: {"north": -10, "south": -29, "east": 154, "west": 138}
            resolution_km: 输出栅格分辨率（公里）
        """
        self.bounds = bounds
        # 5km ≈ 0.045° at Queensland latitude
        self.resolution_deg = resolution_km / 111

    def interpolate_layer(
        self,
        point_data: Dict[str, Dict],
        layer_name: str,
        method: str = 'cubic'
    ) -> Tuple[np.ndarray, dict]:
        """
        插值单个图层

        Args:
            point_data: 点数据字典 {"lat:lon": {layer_name: value, ...}}
            layer_name: 图层名称 (temperature, humidity, etc.)
            method: 插值方法 ('linear', 'cubic', 'nearest')

        Returns:
            (grid_values, metadata)
        """
        # 提取坐标和值
        lats, lons, values = [], [], []

        for key, data in point_data.items():
            value = data.get(layer_name)
            if value is not None:
                lats.append(data["latitude"])
                lons.append(data["longitude"])
                values.append(value)

        if len(values) == 0:
            raise ValueError(f"No valid data for layer {layer_name}")

        # 创建点数组
        points = np.column_stack((lons, lats))
        values = np.array(values)

        # 创建目标网格
        grid_lon = np.arange(
            self.bounds["west"],
            self.bounds["east"],
            self.resolution_deg
        )
        grid_lat = np.arange(
            self.bounds["south"],
            self.bounds["north"],
            self.resolution_deg
        )
        grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)

        # 执行插值
        grid_values = griddata(
            points,
            values,
            (grid_lon_mesh, grid_lat_mesh),
            method=method,
            fill_value=np.nan
        )

        # 翻转纬度（GeoTIFF从北到南）
        grid_values = np.flipud(grid_values)

        # 元数据
        height, width = grid_values.shape
        transform = from_bounds(
            self.bounds["west"],
            self.bounds["south"],
            self.bounds["east"],
            self.bounds["north"],
            width,
            height
        )

        metadata = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": 1,
            "dtype": grid_values.dtype,
            "crs": CRS.from_epsg(4326),
            "transform": transform,
            "nodata": np.nan
        }

        return grid_values, metadata

    def save_geotiff(
        self,
        grid_values: np.ndarray,
        metadata: dict,
        output_path: Path
    ):
        """保存为GeoTIFF"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with rasterio.open(output_path, 'w', **metadata) as dst:
            dst.write(grid_values, 1)

    def process_all_layers(
        self,
        point_data: Dict[str, Dict],
        output_dir: Path,
        layers: List[str] = None
    ) -> Dict[str, Path]:
        """
        处理所有图层

        Returns:
            {layer_name: output_path}
        """
        if layers is None:
            layers = ["temperature", "humidity", "precipitation", "uv_index"]

        output_files = {}

        for layer in layers:
            print(f"Interpolating {layer}...")

            grid, metadata = self.interpolate_layer(point_data, layer)
            output_path = output_dir / f"{layer}_realtime.tif"
            self.save_geotiff(grid, metadata, output_path)

            output_files[layer] = output_path
            print(f"  Saved: {output_path}")

        return output_files
```

**2. 测试脚本**

文件: `tests/test_interpolation.py`

```python
import asyncio
from pathlib import Path
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher
from data_pipeline.processing.common.interpolate_to_raster import RasterInterpolator
from data_pipeline.config.grid_config import GRID_POINTS, QLD_BOUNDS

async def test_interpolation():
    # 获取数据
    async with OpenMeteoFetcher() as fetcher:
        print("Fetching data from Open-Meteo...")
        data = await fetcher.fetch_all_data(GRID_POINTS)
        print(f"Fetched {len(data)} points")

    # 插值
    print("\nInterpolating to raster...")
    interpolator = RasterInterpolator(QLD_BOUNDS, resolution_km=5)
    output_dir = Path("data_pipeline/data/processed/realtime")

    output_files = interpolator.process_all_layers(data, output_dir)

    print("\nGenerated GeoTIFF files:")
    for layer, path in output_files.items():
        size = path.stat().st_size / 1024 / 1024
        print(f"  {layer}: {path} ({size:.2f} MB)")

asyncio.run(test_interpolation())
```

**验收标准**:
- ✅ 成功生成4个GeoTIFF文件
- ✅ 文件格式正确（可用QGIS打开）
- ✅ 坐标系统正确（EPSG:4326）
- ✅ 数值范围合理

---

### 第四步：瓦片生成 ⏳ 待实施

**目标**: 将GeoTIFF转换为PNG地图瓦片

**估计耗时**: 1-2小时

#### 实施详情

**1. 复用现有瓦片生成器**

文件: `data_pipeline/processing/realtime/generate_realtime_tiles.py`

```python
"""
实时数据瓦片生成
"""
from pathlib import Path
import sys

# 复用现有的瓦片生成器
from data_pipeline.processing.common.generate_tiles import TileGenerator

def generate_realtime_tiles(
    input_dir: Path,
    output_dir: Path,
    layers: list = None
):
    """
    为实时数据生成瓦片

    Args:
        input_dir: GeoTIFF所在目录
        output_dir: 瓦片输出目录
        layers: 要处理的图层列表
    """
    if layers is None:
        layers = ["temperature", "humidity", "precipitation", "uv_index"]

    generator = TileGenerator()

    for layer in layers:
        print(f"\nGenerating tiles for {layer}...")

        input_file = input_dir / f"{layer}_realtime.tif"
        layer_tiles_dir = output_dir / layer

        if not input_file.exists():
            print(f"  Skipping - input file not found: {input_file}")
            continue

        # 生成瓦片
        generator.generate_tiles(
            input_raster=input_file,
            output_dir=layer_tiles_dir,
            layer_name=layer,
            zoom_range=(6, 12),
            tile_size=256
        )

        print(f"  Completed: {layer_tiles_dir}")

if __name__ == "__main__":
    input_dir = Path("data_pipeline/data/processed/realtime")
    output_dir = Path("tiles/realtime")

    generate_realtime_tiles(input_dir, output_dir)
```

**验收标准**:
- ✅ 瓦片目录结构正确
- ✅ PNG文件格式正确
- ✅ 颜色映射正确
- ✅ 可在浏览器中加载

---

### 第五步：定时任务调度 ⏳ 待实施

**目标**: 每10分钟自动执行完整更新流程

**估计耗时**: 2-3小时

#### 实施详情

**1. Celery配置**

文件: `data_pipeline/scheduler/celery_config.py`

```python
"""
Celery配置
"""
from celery import Celery
from celery.schedules import crontab
import os

# Celery应用
app = Celery('clisapp')

# 从环境变量加载配置
app.conf.update(
    broker_url=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    timezone='Australia/Brisbane',
    enable_utc=True,
)

# 定时任务配置
app.conf.beat_schedule = {
    'update-climate-data-every-10-minutes': {
        'task': 'data_pipeline.scheduler.update_climate_data.update_all',
        'schedule': 600.0,  # 每10分钟（秒）
    },
}

app.conf.task_routes = {
    'data_pipeline.scheduler.*': {'queue': 'climate_updates'},
}
```

**2. 更新任务**

文件: `data_pipeline/scheduler/update_climate_data.py`

```python
"""
气候数据更新任务
"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from celery import Task

from data_pipeline.scheduler.celery_config import app
from data_pipeline.config.grid_config import GRID_POINTS, QLD_BOUNDS
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher
from data_pipeline.utils.redis_cache import ClimateDataCache
from data_pipeline.processing.common.interpolate_to_raster import RasterInterpolator
from data_pipeline.processing.realtime.generate_realtime_tiles import generate_realtime_tiles

logger = logging.getLogger(__name__)

LAYERS = ["temperature", "humidity", "precipitation", "uv_index"]
DATA_DIR = Path("data_pipeline/data/processed/realtime")
TILES_DIR = Path("tiles/realtime")

class UpdateTask(Task):
    """自定义任务基类"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3}
    retry_backoff = True

@app.task(base=UpdateTask, bind=True)
def update_all(self):
    """完整更新流程"""
    start_time = datetime.now()
    logger.info(f"Starting climate data update: {start_time}")

    try:
        # 运行异步更新
        asyncio.run(_async_update())

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Update completed successfully in {duration:.1f}s")

        return {
            "status": "success",
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Update failed: {e}", exc_info=True)
        raise

async def _async_update():
    """异步更新逻辑"""

    # 1. 获取数据
    logger.info("Step 1: Fetching data from Open-Meteo...")
    cache = ClimateDataCache()

    async with OpenMeteoFetcher(cache=cache) as fetcher:
        data = await fetcher.fetch_and_cache(GRID_POINTS, ttl=3600)

    logger.info(f"Fetched and cached {len(data)} points")

    # 2. 插值生成栅格
    logger.info("Step 2: Interpolating to raster...")
    interpolator = RasterInterpolator(QLD_BOUNDS, resolution_km=5)
    output_files = interpolator.process_all_layers(data, DATA_DIR, LAYERS)
    logger.info(f"Generated {len(output_files)} GeoTIFF files")

    # 3. 生成瓦片
    logger.info("Step 3: Generating tiles...")
    generate_realtime_tiles(DATA_DIR, TILES_DIR, LAYERS)
    logger.info("Tile generation completed")
```

**3. 启动脚本**

文件: `start_scheduler.sh`

```bash
#!/bin/bash
# 启动Celery worker和beat

# 激活虚拟环境
source venv/bin/activate

# 启动worker（后台）
celery -A data_pipeline.scheduler.celery_config worker \
  --loglevel=info \
  --concurrency=2 \
  --queue=climate_updates \
  --detach \
  --logfile=logs/celery_worker.log

# 启动beat scheduler（后台）
celery -A data_pipeline.scheduler.celery_config beat \
  --loglevel=info \
  --detach \
  --logfile=logs/celery_beat.log

echo "Celery scheduler started"
```

**验收标准**:
- ✅ Celery worker启动成功
- ✅ Beat scheduler运行正常
- ✅ 任务按时执行（每10分钟）
- ✅ 完整流程运行无错误

---

### 第六步：Docker部署 ⏳ 待实施

**目标**: 容器化部署整个系统

**估计耗时**: 1-2小时

#### 实施详情

**更新 docker-compose.yml**:

```yaml
version: '3.8'

services:
  # Redis缓存
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes

  # PostgreSQL（可选，用于历史数据）
  postgres:
    image: postgis/postgis:15-3.3
    environment:
      POSTGRES_USER: clisapp
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: clisapp
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  # Backend API
  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8080
    ports:
      - "8080:8080"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://clisapp:${POSTGRES_PASSWORD}@postgres:5432/clisapp
    depends_on:
      - redis
      - postgres
    volumes:
      - ./tiles:/app/tiles
      - ./data:/app/data

  # Tile Server
  tile-server:
    build: .
    command: python data_pipeline/servers/tile_server.py
    ports:
      - "8000:8000"
    volumes:
      - ./tiles:/app/tiles
    depends_on:
      - backend

  # Celery Worker
  celery-worker:
    build: .
    command: celery -A data_pipeline.scheduler.celery_config worker --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0
    depends_on:
      - redis
      - backend
    volumes:
      - ./tiles:/app/tiles
      - ./data:/app/data

  # Celery Beat Scheduler
  celery-beat:
    build: .
    command: celery -A data_pipeline.scheduler.celery_config beat --loglevel=info
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - redis
      - celery-worker
    volumes:
      - ./data:/app/data

volumes:
  redis_data:
  postgres_data:
```

**验收标准**:
- ✅ 所有容器启动成功
- ✅ 服务间通信正常
- ✅ 定时任务执行正常
- ✅ 瓦片可以正常访问

---

## ⏱️ 总体时间估算

| 步骤 | 状态 | 估计耗时 | 实际耗时 |
|------|------|----------|----------|
| Step 1: 数据获取 | ✅ 完成 | 3-4小时 | 4小时 |
| Step 2: Redis缓存 | ⏳ 待实施 | 1-2小时 | - |
| Step 3: 插值处理 | ⏳ 待实施 | 2-3小时 | - |
| Step 4: 瓦片生成 | ⏳ 待实施 | 1-2小时 | - |
| Step 5: 定时调度 | ⏳ 待实施 | 2-3小时 | - |
| Step 6: Docker部署 | ⏳ 待实施 | 1-2小时 | - |
| **总计** | **17%** | **10-16小时** | **4小时** |

**剩余工作量**: 约6-12小时

---

## 🚀 快速开始指南

### 环境要求

```yaml
Python: 3.11+
Redis: 7.0+
PostgreSQL: 15+ (可选)
Docker: 20.10+ (可选)
```

### 安装依赖

```bash
# 克隆项目
cd CLISApp-backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 测试当前进度

```bash
# 测试网格配置
python -m data_pipeline.config.grid_config

# 测试数据获取（10个点）
python test_openmeteo_fetch.py --num-points 10

# 测试UV数据
python test_uv_check.py

# 测试API加权
python test_api_weighting.py
```

### 启动现有服务

```bash
# 启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 启动Backend API
python dev_server.py

# 启动Tile Server
python data_pipeline/servers/tile_server.py
```

---

## 📋 待办事项清单

### 立即执行（第二步）
- [ ] 创建Redis缓存工具类
- [ ] 更新数据获取器集成缓存
- [ ] 测试缓存读写
- [ ] 验证TTL和过期机制

### 近期任务（第三步）
- [ ] 实现插值算法
- [ ] 生成GeoTIFF文件
- [ ] 优化插值性能
- [ ] 测试输出质量

### 中期任务（第四-五步）
- [ ] 集成瓦片生成器
- [ ] 实现增量更新
- [ ] 配置Celery任务
- [ ] 设置定时调度

### 长期任务（可选）
- [ ] 添加WAQI PM2.5数据源
- [ ] 实现历史数据存档
- [ ] 添加监控和告警
- [ ] 性能优化

---

## ⚠️ 已知限制与注意事项

### API限制
1. **Open-Meteo免费额度**: 10,000调用/天
   - 当前使用：9,792调用/天（98%）
   - **不要添加hourly参数**

2. **PM2.5数据不可用**
   - Open-Meteo不覆盖澳大利亚
   - 需要额外数据源（WAQI）

### 技术限制
1. **插值精度**:
   - 依赖原始采样点密度（50km）
   - 偏远地区精度较低

2. **更新延迟**:
   - 完整流程约60-120秒
   - 瓦片生成是瓶颈

### 性能考虑
1. **内存使用**: 插值过程可能占用500MB-1GB
2. **磁盘空间**: 每个图层瓦片约50-100MB
3. **CPU**: 瓦片生成时CPU密集

---

## 🔧 故障排查

### 问题1: API调用超出限额
```
错误: 429 Too Many Requests
解决:
1. 检查更新频率（应为10分钟）
2. 确认没有添加hourly参数
3. 考虑升级到商业版（$50-150/月）
```

### 问题2: UV指数为0
```
问题: UV数据全为0
解决: 检查当前时间是否为夜间（正常现象）
```

### 问题3: 插值结果异常
```
问题: 栅格出现条纹或空白
解决:
1. 检查输入数据是否有None值
2. 尝试更换插值方法（cubic→linear）
3. 增加采样点密度
```

---

## 📚 参考资源

### API文档
- [Open-Meteo API](https://open-meteo.com/en/docs)
- [Open-Meteo Pricing](https://open-meteo.com/en/pricing)
- [WAQI API](https://aqicn.org/api/)

### 技术文档
- [scipy.interpolate](https://docs.scipy.org/doc/scipy/reference/interpolate.html)
- [Rasterio](https://rasterio.readthedocs.io/)
- [Celery](https://docs.celeryproject.org/)

### 项目文档
- [STEP1_SUMMARY.md](./STEP1_SUMMARY.md) - 第一步详细总结
- [requirements.txt](./requirements.txt) - Python依赖

---

## 👥 贡献指南

如果其他开发者接手此项目：

1. **阅读本文档** - 了解整体架构
2. **运行测试** - 验证环境配置
3. **逐步实施** - 按照步骤顺序执行
4. **更新文档** - 记录变更和发现

---

## 📞 联系方式

项目维护者: CLISApp Team
更新日期: 2025-11-20
版本: v1.0

---

**下一步行动**: 开始实施第二步 - Redis缓存层
