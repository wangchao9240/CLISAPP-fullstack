#!/bin/bash
# CLISApp Backend Docker Build & Deploy Script
# 快速构建和部署脚本

set -e  # Exit on error

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# 显示菜单
show_menu() {
    print_header "CLISApp Backend Docker 管理工具"
    echo "请选择操作："
    echo ""
    echo "  1) 构建 Docker 镜像"
    echo "  2) 启动服务 (docker-compose)"
    echo "  3) 停止服务"
    echo "  4) 查看日志"
    echo "  5) 查看服务状态"
    echo "  6) 导出镜像为文件"
    echo "  7) 推送到 Docker Hub"
    echo "  8) 清理容器和镜像"
    echo "  9) 进入容器 (bash)"
    echo "  0) 退出"
    echo ""
}

# 检查 Docker 是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装！请先安装 Docker。"
        echo "访问: https://www.docker.com/get-started"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_warning "docker-compose 未安装，将使用 docker compose 命令"
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    print_success "Docker 环境检查通过"
}

# 构建镜像
build_image() {
    print_header "构建 Docker 镜像"
    
    read -p "请输入镜像标签（默认: clisapp-backend:latest）: " IMAGE_TAG
    IMAGE_TAG=${IMAGE_TAG:-clisapp-backend:latest}
    
    print_info "开始构建镜像: $IMAGE_TAG"
    docker build -t "$IMAGE_TAG" .
    
    print_success "镜像构建完成！"
    docker images | grep clisapp-backend
}

# 启动服务
start_services() {
    print_header "启动 Docker Compose 服务"
    
    # 检查环境文件
    if [ ! -f .env ]; then
        print_warning ".env 文件不存在"
        read -p "是否从 env.example 创建 .env 文件？(y/n): " CREATE_ENV
        if [ "$CREATE_ENV" == "y" ]; then
            cp env.example .env
            print_success "已创建 .env 文件，请编辑填入你的配置"
            read -p "按 Enter 继续..."
        fi
    fi
    
    print_info "启动服务..."
    $COMPOSE_CMD up -d
    
    print_success "服务已启动！"
    echo ""
    print_info "服务地址："
    echo "  - API: http://localhost:8080/api/v1/health"
    echo "  - 文档: http://localhost:8080/docs"
    echo ""
    
    sleep 3
    $COMPOSE_CMD ps
}

# 停止服务
stop_services() {
    print_header "停止服务"
    
    read -p "是否删除数据卷？(y/n，默认: n): " REMOVE_VOLUMES
    
    if [ "$REMOVE_VOLUMES" == "y" ]; then
        print_warning "将删除所有数据卷（包括 Redis 数据）"
        $COMPOSE_CMD down -v
    else
        $COMPOSE_CMD down
    fi
    
    print_success "服务已停止"
}

# 查看日志
view_logs() {
    print_header "查看日志"
    
    echo "请选择："
    echo "  1) 后端日志"
    echo "  2) Redis 日志"
    echo "  3) 所有日志"
    read -p "选择 (1-3): " LOG_CHOICE
    
    case $LOG_CHOICE in
        1)
            $COMPOSE_CMD logs -f backend
            ;;
        2)
            $COMPOSE_CMD logs -f redis
            ;;
        3)
            $COMPOSE_CMD logs -f
            ;;
        *)
            print_error "无效选择"
            ;;
    esac
}

# 查看状态
view_status() {
    print_header "服务状态"
    
    print_info "容器状态："
    $COMPOSE_CMD ps
    
    echo ""
    print_info "资源使用："
    docker stats --no-stream clisapp-backend clisapp-redis 2>/dev/null || print_warning "容器未运行"
    
    echo ""
    print_info "健康检查："
    curl -s http://localhost:8080/api/v1/health | python3 -m json.tool 2>/dev/null || print_warning "服务未响应"
}

# 导出镜像
export_image() {
    print_header "导出镜像为文件"
    
    read -p "请输入镜像名（默认: clisapp-backend:latest）: " IMAGE_NAME
    IMAGE_NAME=${IMAGE_NAME:-clisapp-backend:latest}
    
    read -p "请输入输出文件名（默认: clisapp-backend.tar）: " OUTPUT_FILE
    OUTPUT_FILE=${OUTPUT_FILE:-clisapp-backend.tar}
    
    print_info "导出镜像: $IMAGE_NAME -> $OUTPUT_FILE"
    docker save "$IMAGE_NAME" -o "$OUTPUT_FILE"
    
    # 压缩
    read -p "是否压缩为 .tar.gz？(y/n): " COMPRESS
    if [ "$COMPRESS" == "y" ]; then
        print_info "压缩中..."
        gzip "$OUTPUT_FILE"
        OUTPUT_FILE="${OUTPUT_FILE}.gz"
    fi
    
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    print_success "导出完成！文件: $OUTPUT_FILE (大小: $FILE_SIZE)"
    
    echo ""
    print_info "别人可以这样加载镜像："
    if [ "$COMPRESS" == "y" ]; then
        echo "  gunzip $OUTPUT_FILE"
        echo "  docker load -i ${OUTPUT_FILE%.gz}"
    else
        echo "  docker load -i $OUTPUT_FILE"
    fi
}

# 推送到 Docker Hub
push_to_hub() {
    print_header "推送到 Docker Hub"
    
    read -p "请输入你的 Docker Hub 用户名: " DOCKER_USERNAME
    if [ -z "$DOCKER_USERNAME" ]; then
        print_error "用户名不能为空"
        return
    fi
    
    read -p "请输入镜像版本（默认: latest）: " VERSION
    VERSION=${VERSION:-latest}
    
    IMAGE_NAME="$DOCKER_USERNAME/clisapp-backend:$VERSION"
    
    print_info "登录 Docker Hub..."
    docker login
    
    print_info "打标签: $IMAGE_NAME"
    docker tag clisapp-backend:latest "$IMAGE_NAME"
    
    print_info "推送镜像..."
    docker push "$IMAGE_NAME"
    
    print_success "推送完成！"
    echo ""
    print_info "别人可以这样拉取镜像："
    echo "  docker pull $IMAGE_NAME"
    echo "  docker run -d -p 8080:8080 $IMAGE_NAME"
}

# 清理
cleanup() {
    print_header "清理容器和镜像"
    
    print_warning "这将删除："
    echo "  - 停止的容器"
    echo "  - 未使用的镜像"
    echo "  - 构建缓存"
    echo ""
    
    read -p "确认继续？(y/n): " CONFIRM
    if [ "$CONFIRM" != "y" ]; then
        print_info "已取消"
        return
    fi
    
    print_info "清理停止的容器..."
    docker container prune -f
    
    print_info "清理未使用的镜像..."
    docker image prune -f
    
    print_info "清理构建缓存..."
    docker builder prune -f
    
    print_success "清理完成！"
}

# 进入容器
enter_container() {
    print_header "进入容器"
    
    print_info "进入 clisapp-backend 容器..."
    $COMPOSE_CMD exec backend bash || {
        print_error "无法进入容器，请确保容器正在运行"
        print_info "提示：先运行选项 2 启动服务"
    }
}

# 主循环
main() {
    check_docker
    
    while true; do
        show_menu
        read -p "请选择 (0-9): " choice
        
        case $choice in
            1)
                build_image
                ;;
            2)
                start_services
                ;;
            3)
                stop_services
                ;;
            4)
                view_logs
                ;;
            5)
                view_status
                ;;
            6)
                export_image
                ;;
            7)
                push_to_hub
                ;;
            8)
                cleanup
                ;;
            9)
                enter_container
                ;;
            0)
                print_info "再见！"
                exit 0
                ;;
            *)
                print_error "无效选择，请输入 0-9"
                ;;
        esac
        
        echo ""
        read -p "按 Enter 继续..."
    done
}

# 运行主程序
main

