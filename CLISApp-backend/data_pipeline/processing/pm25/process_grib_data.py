#!/usr/bin/env python3
"""
GRIB数据处理脚本 - 专门处理CAMS GRIB格式的PM2.5数据
"""

import xarray as xr
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class GRIBDataProcessor:
    def __init__(self):
        self.target_crs = "EPSG:4326"  # WGS84
        self.web_mercator_crs = "EPSG:3857"  # Web Mercator for tiles
    
    def process_grib_pm25_for_tiles(self, grib_file, output_dir="data_pipeline/data/processed/pm25"):
        """
        处理GRIB格式的PM2.5数据为瓦片生成准备
        
        Args:
            grib_file: 输入GRIB文件
            output_dir: 输出目录
        """
        logger.info(f"开始处理GRIB数据文件: {grib_file}")
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            # 使用cfgrib读取GRIB数据
            logger.info("正在读取GRIB文件...")
            ds = xr.open_dataset(grib_file, engine='cfgrib')
            
            logger.info("GRIB文件读取成功")
            logger.info(f"数据变量: {list(ds.data_vars.keys())}")
            logger.info(f"坐标: {list(ds.coords.keys())}")
            logger.info(f"数据形状: {ds.dims}")
            
            # 查找PM2.5变量 (GRIB文件中可能有不同的变量名)
            pm25_vars = []
            for var in ds.data_vars:
                var_name = str(var).lower()
                if any(keyword in var_name for keyword in ['pm2p5', 'pm25', 'particulate', 'mass_density', 'dust']):
                    pm25_vars.append(var)
                    logger.info(f"找到可能的PM2.5变量: {var}")
                    if hasattr(ds[var], 'long_name'):
                        logger.info(f"  长名称: {ds[var].long_name}")
                    if hasattr(ds[var], 'units'):
                        logger.info(f"  单位: {ds[var].units}")
            
            if not pm25_vars:
                # 如果没找到明确的PM2.5变量，使用第一个数据变量
                pm25_vars = [list(ds.data_vars.keys())[0]]
                logger.warning(f"未找到明确的PM2.5变量，使用第一个变量: {pm25_vars[0]}")
            
            pm25_var = pm25_vars[0]
            pm25_data = ds[pm25_var]
            
            logger.info(f"使用变量: {pm25_var}")
            logger.info(f"原始数据形状: {pm25_data.shape}")
            logger.info(f"原始数据单位: {pm25_data.attrs.get('units', 'unknown')}")
            logger.info(f"原始数据范围: {pm25_data.min().item():.2e} - {pm25_data.max().item():.2e}")
            
            # 处理数据的单位和维度
            # GRIB文件通常包含多个时间步 (step维度)
            if 'step' in pm25_data.dims:
                logger.info(f"步长维度: {len(pm25_data.step)} 个时间步")
                logger.info(f"步长范围: {pm25_data.step.min().values} 到 {pm25_data.step.max().values}")
                
                # 计算时间平均值
                pm25_mean = pm25_data.mean(dim='step', skipna=True)
                logger.info("计算步长平均值")
            elif 'time' in pm25_data.dims:
                logger.info(f"时间维度: {len(pm25_data.time)} 个时间步")
                logger.info(f"时间范围: {pm25_data.time.min().values} 到 {pm25_data.time.max().values}")
                
                # 计算时间平均值
                pm25_mean = pm25_data.mean(dim='time', skipna=True)
                logger.info("计算时间平均值")
            else:
                pm25_mean = pm25_data
                logger.info("数据不包含时间或步长维度")
            
            # 检查和转换单位
            if hasattr(pm25_data, 'units'):
                units = pm25_data.units
                if units == 'kg m**-3':
                    # 转换 kg/m³ → μg/m³
                    pm25_ugm3 = pm25_mean * 1e9
                    logger.info("单位转换: kg/m³ → μg/m³")
                elif units == 'kg kg**-1':
                    # 假设近地面空气密度约为 1.2 kg/m³
                    pm25_ugm3 = pm25_mean * 1.2 * 1e9
                    logger.info("单位转换: kg/kg → μg/m³ (假设空气密度 1.2 kg/m³)")
                else:
                    pm25_ugm3 = pm25_mean
                    logger.warning(f"未知单位: {units}, 不进行转换")
            else:
                # 检查数据范围来推测单位
                data_max = pm25_mean.max().item()
                if data_max < 1e-6:
                    # 很可能是 kg/m³
                    pm25_ugm3 = pm25_mean * 1e9
                    logger.info("根据数据范围推测单位转换: kg/m³ → μg/m³")
                else:
                    pm25_ugm3 = pm25_mean
                    logger.info("数据范围显示可能已经是 μg/m³")
            
            logger.info(f"处理后数据范围: {pm25_ugm3.min().item():.2f} - {pm25_ugm3.max().item():.2f} μg/m³")
            
            # 输出处理后的数据 (NetCDF格式)
            output_file = os.path.join(output_dir, "pm25_qld_cams_processed.nc")
            
            # 更新属性
            pm25_ugm3.attrs = {
                'long_name': 'CAMS PM2.5 mass concentration (time-averaged)',
                'units': 'μg m-3',
                'standard_name': 'mass_concentration_of_pm2p5_ambient_aerosol_particles_in_air',
                'description': 'Real CAMS PM2.5 data processed for tile generation',
                'source': 'ECMWF CAMS Global Atmospheric Composition Forecasts'
            }
            
            pm25_ugm3.to_netcdf(output_file)
            logger.info(f"处理后数据保存: {output_file}")
            
            # 生成GeoTIFF (用于瓦片生成)
            geotiff_file = self.export_to_geotiff(pm25_ugm3, output_dir)
            
            return output_file, geotiff_file
            
        except Exception as e:
            logger.error(f"GRIB文件处理失败: {e}")
            raise
        finally:
            if 'ds' in locals():
                ds.close()
    
    def export_to_geotiff(self, data_array, output_dir):
        """导出为GeoTIFF格式"""
        geotiff_file = os.path.join(output_dir, "pm25_qld_cams_processed.tif")
        
        logger.info(f"导出GeoTIFF: {geotiff_file}")
        
        # 获取坐标
        lats = data_array.latitude.values
        lons = data_array.longitude.values
        
        logger.info(f"经度范围: {lons.min():.2f} - {lons.max():.2f}")
        logger.info(f"纬度范围: {lats.min():.2f} - {lats.max():.2f}")
        
        # 检查坐标顺序
        if lats[0] < lats[-1]:
            logger.info("纬度需要翻转 (南→北 改为 北→南)")
            data_values = np.flipud(data_array.values)
            lats = lats[::-1]
        else:
            data_values = data_array.values
        
        # 创建变换矩阵
        transform = from_bounds(
            lons.min(), lats.min(), 
            lons.max(), lats.max(),
            len(lons), len(lats)
        )
        
        # 处理NaN值
        data_values = np.nan_to_num(data_values, nan=0.0)
        
        # 写入GeoTIFF
        with rasterio.open(
            geotiff_file, 'w',
            driver='GTiff',
            height=len(lats),
            width=len(lons),
            count=1,
            dtype=rasterio.float32,
            crs=self.target_crs,
            transform=transform,
            compress='lzw',
        ) as dst:
            dst.write(data_values.astype(rasterio.float32), 1)
            
            # 添加元数据
            dst.update_tags(
                AREA_OR_POINT='Area',
                DESCRIPTION='CAMS PM2.5 mass concentration for Queensland, Australia',
                UNITS='μg/m³',
                SOURCE='ECMWF CAMS Global Atmospheric Composition Forecasts'
            )
        
        # 验证GeoTIFF
        with rasterio.open(geotiff_file) as src:
            logger.info(f"GeoTIFF验证: {src.width} x {src.height} pixels")
            logger.info(f"投影坐标系: {src.crs}")
            logger.info(f"数据范围: {src.read(1).min():.2f} - {src.read(1).max():.2f}")
        
        logger.info(f"GeoTIFF导出完成: {geotiff_file}")
        return geotiff_file
    
    def inspect_grib_file(self, grib_file):
        """检查GRIB文件内容"""
        logger.info(f"检查GRIB文件: {grib_file}")
        
        try:
            ds = xr.open_dataset(grib_file, engine='cfgrib')
            
            print("=== GRIB文件信息 ===")
            print(f"文件: {grib_file}")
            print(f"大小: {os.path.getsize(grib_file) / 1024:.2f} KB")
            print()
            
            print("数据变量:")
            for var in ds.data_vars:
                print(f"  {var}:")
                if hasattr(ds[var], 'long_name'):
                    print(f"    长名称: {ds[var].long_name}")
                if hasattr(ds[var], 'units'):
                    print(f"    单位: {ds[var].units}")
                print(f"    形状: {ds[var].shape}")
                print(f"    维度: {ds[var].dims}")
                print(f"    数据范围: {ds[var].min().item():.2e} - {ds[var].max().item():.2e}")
                print()
            
            print("坐标:")
            for coord in ds.coords:
                print(f"  {coord}: {ds.coords[coord].shape} {ds.coords[coord].dims}")
                if coord in ['time']:
                    print(f"    范围: {ds.coords[coord].min().values} 到 {ds.coords[coord].max().values}")
                else:
                    print(f"    范围: {ds.coords[coord].min().item():.2f} 到 {ds.coords[coord].max().item():.2f}")
            
            print(f"\n全局属性:")
            for attr in ds.attrs:
                print(f"  {attr}: {ds.attrs[attr]}")
                
        except Exception as e:
            logger.error(f"检查GRIB文件失败: {e}")
        finally:
            if 'ds' in locals():
                ds.close()

def main():
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    if len(sys.argv) > 1:
        grib_file = sys.argv[1]
    else:
        # 自动查找最新的GRIB文件
        data_dir = Path("data_pipeline/data/raw/pm25")
        grib_files = list(data_dir.glob("*.grib"))
        
        if not grib_files:
            print("❌ 未找到GRIB数据文件")
            print("   请先运行: python data_pipeline/downloads/pm25/download_pm25.py")
            sys.exit(1)
        
        # 使用最新的文件
        grib_file = max(grib_files, key=os.path.getctime)
    
    try:
        processor = GRIBDataProcessor()
        
        # 先检查文件内容
        print("🔍 检查GRIB文件内容:")
        processor.inspect_grib_file(str(grib_file))
        print()
        
        # 处理数据
        print("⚙️ 开始处理数据...")
        processed_file, geotiff_file = processor.process_grib_pm25_for_tiles(str(grib_file))
        
        print("✅ GRIB数据处理完成!")
        print(f"📄 处理后NetCDF: {processed_file}")
        print(f"🗺️  GeoTIFF文件: {geotiff_file}")
        print("\n📝 下一步:")
        print("   python data_pipeline/processing/common/generate_tiles.py data_pipeline/data/processed/pm25/pm25_qld_cams_processed.tif")
        
    except Exception as e:
        print(f"❌ GRIB数据处理失败: {e}")
        logger.error(f"GRIB数据处理失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
