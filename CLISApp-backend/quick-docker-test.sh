#!/bin/bash
# 快速构建和验证Docker镜像
# Quick Docker Build & Validation Script

set -e

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  CLISApp Backend Docker 构建和验证${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# 步骤 1: 构建镜像
echo -e "${YELLOW}📦 步骤 1/5: 构建 Docker 镜像...${NC}"
echo ""
docker build -t clisapp-backend:latest . || {
    echo -e "${RED}❌ 构建失败！${NC}"
    exit 1
}

echo ""
echo -e "${GREEN}✅ 镜像构建成功！${NC}"
echo ""

# 步骤 2: 查看镜像信息
echo -e "${YELLOW}📊 步骤 2/5: 查看镜像信息...${NC}"
echo ""
docker images clisapp-backend:latest
echo ""

IMAGE_SIZE=$(docker images clisapp-backend:latest --format "{{.Size}}")
echo -e "${GREEN}✅ 镜像大小: $IMAGE_SIZE${NC}"
echo ""

# 步骤 3: 启动容器
echo -e "${YELLOW}🚀 步骤 3/5: 启动测试容器...${NC}"
echo ""

# 停止并删除已存在的测试容器
docker rm -f clisapp-backend-test 2>/dev/null || true

# 启动新容器
docker run -d \
    --name clisapp-backend-test \
    -p 8080:8080 \
    -v "$(pwd)/tiles:/app/tiles:ro" \
    -e DEBUG=true \
    -e LOG_LEVEL=INFO \
    clisapp-backend:latest

echo -e "${GREEN}✅ 容器已启动！${NC}"
echo ""

# 步骤 4: 等待服务启动
echo -e "${YELLOW}⏳ 步骤 4/5: 等待服务启动...${NC}"
echo ""

for i in {1..15}; do
    if curl -s http://localhost:8080/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 服务已就绪！（用时 ${i} 秒）${NC}"
        break
    fi
    echo -n "."
    sleep 1
    if [ $i -eq 15 ]; then
        echo ""
        echo -e "${RED}❌ 服务启动超时${NC}"
        echo ""
        echo "查看容器日志："
        docker logs clisapp-backend-test
        exit 1
    fi
done

echo ""

# 步骤 5: 验证功能
echo -e "${YELLOW}🧪 步骤 5/5: 验证服务功能...${NC}"
echo ""

# 5.1 健康检查
echo "1️⃣  健康检查 API："
HEALTH_RESPONSE=$(curl -s http://localhost:8080/api/v1/health)
if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}   ✅ 健康检查通过${NC}"
    echo "$HEALTH_RESPONSE" | python3 -m json.tool | head -10
else
    echo -e "${RED}   ❌ 健康检查失败${NC}"
fi
echo ""

# 5.2 API文档
echo "2️⃣  API 文档："
DOC_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/docs)
if [ "$DOC_STATUS" = "200" ]; then
    echo -e "${GREEN}   ✅ API 文档可访问 (http://localhost:8080/docs)${NC}"
else
    echo -e "${RED}   ❌ API 文档不可访问 (HTTP $DOC_STATUS)${NC}"
fi
echo ""

# 5.3 瓦片服务
echo "3️⃣  瓦片服务状态："
TILE_STATUS=$(curl -s http://localhost:8080/api/v1/tiles/status)
if echo "$TILE_STATUS" | grep -q "layers"; then
    echo -e "${GREEN}   ✅ 瓦片服务正常${NC}"
    echo "$TILE_STATUS" | python3 -m json.tool | head -15
else
    echo -e "${YELLOW}   ⚠️  瓦片数据可能未加载${NC}"
fi
echo ""

# 5.4 测试一个瓦片请求
echo "4️⃣  测试瓦片请求："
TILE_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/tiles/pm25/8/241/155.png)
if [ "$TILE_HTTP_CODE" = "200" ] || [ "$TILE_HTTP_CODE" = "404" ]; then
    if [ "$TILE_HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}   ✅ 瓦片请求成功 (HTTP 200)${NC}"
    else
        echo -e "${YELLOW}   ⚠️  瓦片未找到 (HTTP 404 - 正常，如果瓦片文件不存在)${NC}"
    fi
else
    echo -e "${RED}   ❌ 瓦片请求失败 (HTTP $TILE_HTTP_CODE)${NC}"
fi
echo ""

# 5.5 查看容器状态
echo "5️⃣  容器运行状态："
docker ps --filter name=clisapp-backend-test --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 总结
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}🎉 验证完成！${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo "📍 服务地址："
echo "   - API 文档: http://localhost:8080/docs"
echo "   - 健康检查: http://localhost:8080/api/v1/health"
echo "   - 详细状态: http://localhost:8080/api/v1/health/detailed"
echo ""
echo "🔍 有用的命令："
echo "   - 查看日志: docker logs -f clisapp-backend-test"
echo "   - 进入容器: docker exec -it clisapp-backend-test bash"
echo "   - 停止容器: docker stop clisapp-backend-test"
echo "   - 删除容器: docker rm -f clisapp-backend-test"
echo ""
echo "💾 导出镜像："
echo "   docker save clisapp-backend:latest -o clisapp-backend.tar"
echo "   gzip clisapp-backend.tar  # 压缩"
echo ""
echo "🚀 使用 docker-compose 启动完整服务（包括Redis）："
echo "   docker-compose up -d"
echo ""

