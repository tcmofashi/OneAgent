#!/bin/bash
# OneAgent 分布式测试集群停止脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")/.."

cd "$PROJECT_ROOT"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== 停止 OneAgent 分布式测试集群 ===${NC}"
echo ""

# 停止容器
echo -e "${YELLOW}[1/3] 停止 Docker 容器...${NC}"
if docker ps -a | grep -q "oneagent-"; then
    if docker-compose -f infrastructure/docker-compose.test.yml down 2>/dev/null; then
        echo -e "${GREEN}✓ Docker Compose 停止完成${NC}"
    elif docker compose -f infrastructure/docker-compose.test.yml down 2>/dev/null; then
        echo -e "${GREEN}✓ Docker Compose (新语法) 停止完成${NC}"
    else
        echo -e "${YELLOW}手动停止容器...${NC}"
        docker ps -a --filter "name=oneagent-" -q | xargs -r docker stop 2>/dev/null || true
        docker ps -a --filter "name=oneagent-" -q | xargs -r docker rm 2>/dev/null || true
    fi
else
    echo -e "${GREEN}✓ 没有运行的容器${NC}"
fi
echo ""

# 收集日志
echo -e "${YELLOW}[2/3] 收集容器日志...${NC}"
LOG_DIR=".OneAgent/cluster_logs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
for NODE in root-0 sub-0 sub-1 sub-2; do
    if docker logs oneagent-${NODE} 2>/dev/null; then
        docker logs oneagent-${NODE} > "${LOG_DIR}/${NODE}_${TIMESTAMP}.log" 2>&1
        echo -e "${GREEN}✓ ${NODE} 日志已保存${NC}"
    fi
done
echo ""

# 清理旧日志（保留最近 10 个）
echo -e "${YELLOW}[3/3] 清理旧日志...${NC}"
cd "$LOG_DIR"
ls -t *.log 2>/dev/null | tail -n +11 | xargs -r rm -f 2>/dev/null || true
echo -e "${GREEN}✓ 旧日志已清理${NC}"
echo ""

echo -e "${GREEN}=== 集群停止完成 ===${NC}"
echo ""
echo "日志位置: ${PROJECT_ROOT}/${LOG_DIR}"
