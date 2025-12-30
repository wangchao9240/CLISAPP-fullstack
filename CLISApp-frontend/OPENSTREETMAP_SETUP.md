# OpenStreetMap 集成指南

## 🗺️ 免费地图解决方案

CLISApp 现在使用 **OpenStreetMap** 作为默认地图提供商，完全免费且无需任何 API 密钥！

### 🎯 **优势**

✅ **完全免费** - 无需信用卡，无使用限制  
✅ **开源数据** - 社区维护，全球覆盖  
✅ **澳大利亚支持** - 昆士兰地区数据完整  
✅ **学术友好** - 非商业项目的完美选择  
✅ **多种样式** - 提供多种地图样式选择  

### 🛠️ **技术实现**

#### **架构层次**
```
用户看到的地图 = OpenStreetMap 基础层 + 气候数据层

OpenStreetMap 基础层             气候数据层 (我们的后端)
├── 街道和道路                    ├── Copernicus CAMS (PM2.5, UV等)
├── 城市和地名                    ├── NASA GPM (降水)
├── 行政边界                      ├── NASA MERRA-2 (温度, 湿度)
└── 地理特征                      └── 处理成瓦片格式
```

#### **瓦片服务器**
我们使用多个 OSM 瓦片服务器确保可靠性：

- **CartoDB Light** (默认) - 简洁的浅色主题
- **CartoDB Dark** - 深色主题
- **Standard OSM** - 经典 OpenStreetMap 样式
- **OpenTopoMap** - 地形图样式

### 🎮 **使用方法**

#### **地图提供商切换**
应用右下角有 "Map Style" 切换器：
- **OSM** - OpenStreetMap (免费，推荐)
- **Native** - 平台原生地图 (需要配置)
- **LibreGL** - 矢量地图 (未来功能)

#### **功能特性**
- ✅ **平移缩放** - 支持所有标准地图操作
- ✅ **用户位置** - 显示当前位置 (需要权限)
- ✅ **气候数据层** - 叠加后端气候瓦片
- ✅ **层级切换** - LGA ↔ Suburb 切换
- ✅ **连接状态** - 实时显示后端连接

### 🚀 **测试应用**

#### **1. 启动后端**
```bash
cd CLISApp-backend
source venv/bin/activate
python dev_server.py
```

#### **2. 启动前端**
```bash
cd CLISApp-frontend
npm start
npm run ios  # 或 npm run android
```

#### **3. 验证功能**
- ✅ 地图加载 OpenStreetMap 瓦片
- ✅ ConnectionStatus 显示 "Connected"
- ✅ 可以看到昆士兰的街道和城市
- ✅ 气候数据层正确叠加
- ✅ LGA/Suburb 切换工作正常

### 🔧 **配置选项**

#### **瓦片服务器配置**
在 `src/constants/mapConfig.ts` 中可以修改瓦片源：

```typescript
export const OSM_TILE_SERVERS = {
  standard: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  cartodb_light: 'https://cartodb-basemaps-a.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
  cartodb_dark: 'https://cartodb-basemaps-a.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png',
  topo: 'https://tile.opentopomap.org/{z}/{x}/{y}.png',
};
```

#### **默认地图提供商**
在 `src/store/settingsStore.ts` 中可以修改默认设置：

```typescript
const defaultSettings = {
  mapProvider: 'openstreetmap', // 默认使用 OSM
  // ...
};
```

### 📱 **权限设置**

#### **位置权限**
应用需要位置权限来显示用户当前位置：

**iOS**: `ios/CLISApp/Info.plist`
```xml
<key>NSLocationWhenInUseUsageDescription</key>
<string>CLISApp needs location access to show climate data for your area</string>
```

**Android**: `android/app/src/main/AndroidManifest.xml`
```xml
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
```

### 🔍 **故障排除**

#### **问题 1: 地图瓦片不加载**
**解决方案**:
- 检查网络连接
- 尝试切换不同的瓦片服务器
- 检查防火墙设置

#### **问题 2: 地图显示空白**
**解决方案**:
- 确认应用有网络权限
- 检查瓦片 URL 是否正确
- 尝试重启应用

#### **问题 3: 气候数据层不显示**
**解决方案**:
- 确认后端服务器运行正常
- 检查 ConnectionStatus 是否显示 "Connected"
- 验证瓦片 API 端点工作正常

### 🌟 **与 Google Maps 的对比**

| 特性 | OpenStreetMap | Google Maps |
|------|---------------|-------------|
| **费用** | 完全免费 | 有免费额度，超出收费 |
| **数据质量** | 很好 | 优秀 |
| **昆士兰覆盖** | 完整 | 完整 |
| **API 密钥** | 不需要 | 需要 |
| **商业使用** | 允许 | 有限制 |
| **自定义** | 高度可定制 | 有限 |

### 🎓 **学术项目优势**

对于 CLISApp 这样的学术项目，OpenStreetMap 提供：
- ✅ **零成本** - 无需担心超出免费额度
- ✅ **无依赖** - 不依赖任何商业服务
- ✅ **透明度** - 开源数据，可验证
- ✅ **教育价值** - 展示开源GIS技术

### 📚 **相关资源**

- [OpenStreetMap 官网](https://www.openstreetmap.org/)
- [CartoDB 瓦片服务](https://carto.com/basemaps/)
- [React Native Maps 文档](https://github.com/react-native-maps/react-native-maps)
- [OSM 瓦片服务器列表](https://wiki.openstreetmap.org/wiki/Tile_servers)

---

**🎉 现在享受免费的地图服务吧！**  
无需任何 API 密钥，立即启动你的 CLISApp！
