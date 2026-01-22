#!/bin/bash
# OneAgent 分布式测试集群启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR"/../../.. && pwd)"

cd "$PROJECT_ROOT"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== OneAgent 分布式测试集群 ===${NC}"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: 未安装 Docker${NC}"
    echo "请安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${YELLOW}警告: 未安装 docker-compose，尝试使用 docker compose${NC}"
fi

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}错误: Docker 未运行${NC}"
    echo "请启动 Docker: sudo systemctl start docker"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境检查通过${NC}"
echo ""

# 检查必要文件
echo -e "${YELLOW}[1/5] 检查必要文件...${NC}"
if [ ! -f "infrastructure/Dockerfile.test" ]; then
    echo -e "${RED}错误: Dockerfile.test 不存在${NC}"
    exit 1
fi

if [ ! -f "infrastructure/docker-compose.test.yml" ]; then
    echo -e "${RED}错误: docker-compose.test.yml 不存在${NC}"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}错误: requirements.txt 不存在${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 所有必要文件存在${NC}"
echo ""

# 停止已存在的容器
echo -e "${YELLOW}[2/5] 清理旧容器...${NC}"
if docker ps -a | grep -q "oneagent-"; then
    echo "停止并移除旧容器..."
    docker-compose -f infrastructure/docker-compose.test.yml down 2>/dev/null || docker compose -f infrastructure/docker-compose.test.yml down 2>/dev/null || true
fi
echo -e "${GREEN}✓ 旧容器已清理${NC}"
echo ""

# 创建必要的目录
echo -e "${YELLOW}[3/5] 创建目录...${NC}"
mkdir -p logs
mkdir -p .OneAgent/cluster_logs
echo -e "${GREEN}✓ 目录创建完成${NC}"
echo ""

# 构建镜像
echo -e "${YELLOW}[4/5] 构建 Docker 镜像...${NC}"
echo "这可能需要几分钟时间..."

if docker-compose -f infrastructure/docker-compose.test.yml build 2>/dev/null; then
    echo -e "${GREEN}✓ Docker Compose 构建完成${NC}"
elif docker compose -f infrastructure/docker-compose.test.yml build 2>/dev/null; then
    echo -e "${GREEN}✓ Docker Compose (新语法) 构建完成${NC}"
else
    echo -e "${RED}错误: Docker 镜像构建失败${NC}"
    exit 1
fi
echo ""

# 启动集群
echo -e "${YELLOW}[5/5] 启动测试集群...${NC}"
echo "启动 1 个主控节点 + 3 个工作节点..."

if docker-compose -f infrastructure/docker-compose.test.yml up -d 2>/dev/null; then
    echo -e "${GREEN}✓ Docker Compose 启动完成${NC}"
elif docker compose -f infrastructure/docker-compose.test.yml up -d 2>/dev/null; then
    echo -e "${GREEN}✓ Docker Compose (新语法) 启动完成${NC}"
else
    echo -e "${RED}错误: 集群启动失败${NC}"
    exit 1
fi
echo ""

# 等待健康检查
echo -e "${YELLOW}等待节点就绪...${NC}"
MAX_WAIT=30
WAITED=0

while [ $WAITED -lt $MAX_WAIT ]; do
    READY=0
    for PORT in 8000 8001 8002 8003; do
        if curl -sf http://localhost:$PORT/health > /dev/null 2>&1; then
            READY=$((READY + 1))
        fi
    done

    if [ $READY -eq 4 ]; then
        echo -e "${GREEN}✓ 所有 4 个节点已就绪${NC}"
        break
    fi

    echo -n "."
    sleep 1
    WAITED=$((WAITED + 1))
done
echo ""

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e "${RED}警告: 部分节点可能未就绪，但继续...${NC}"
fi

# 显示集群状态
echo -e "${GREEN}=== 集群状态 ===${NC}"
docker ps --filter "name=oneagent-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# 保存集群信息
echo -e "${GREEN}集群启动完成！${NC}"
echo ""
echo "节点访问地址："
echo "  主控节点 (RootOneAgent): http://localhost:8000"
echo "  工作节点 1:             http://localhost:8001"
echo "  工作节点 2:             http://localhost:8002"
echo "  工作节点 3:             http://localhost:8003"
echo ""
echo "测试命令："
echo "  pytest tests/distributed/ -v -m distributed"
echo ""
echo "停止集群："
echo "  ./tests/distributed/scripts/stop_cluster.sh"
