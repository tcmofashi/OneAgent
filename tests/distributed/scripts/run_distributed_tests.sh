#!/bin/bash
# OneAgent 分布式测试运行脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")/.."

cd "$PROJECT_ROOT"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== OneAgent 分布式测试框架 ===${NC}"
echo ""

# 检查依赖
echo -e "${YELLOW}[检查依赖]${NC}"
MISSING_DEPS=0

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}✗ 未安装 Python3${NC}"
    MISSING_DEPS=$((MISSING_DEPS + 1))
else
    echo -e "${GREEN}✓ Python3: $(python3 --version)${NC}"
fi

# 检查 pytest
if ! python3 -m pytest --version &> /dev/null 2>&1; then
    echo -e "${RED}✗ 未安装 pytest${NC}"
    echo "请安装: pip install pytest pytest-asyncio"
    MISSING_DEPS=$((MISSING_DEPS + 1))
else
    echo -e "${GREEN}✓ pytest: $(python3 -m pytest --version)${NC}"
fi

# 检查 httpx
if ! python3 -c "import httpx" 2>/dev/null; then
    echo -e "${YELLOW}⚠ 未安装 httpx（用于测试）${NC}"
    echo "可选: pip install httpx"
else
    echo -e "${GREEN}✓ httpx: 已安装${NC}"
fi

# 检查 Docker（可选）
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✓ Docker: $(docker --version)${NC}"
    DOCKER_AVAILABLE=true
else
    echo -e "${YELLOW}⚠ 未安装 Docker（跳过容器测试）${NC}"
    DOCKER_AVAILABLE=false
fi

echo ""

if [ $MISSING_DEPS -gt 0 ]; then
    echo -e "${RED}错误: 缺少必需依赖${NC}"
    exit 1
fi

# 检查参数
USE_DOCKER=${USE_DOCKER:-"false"}
TEST_PATTERN=${TEST_PATTERN:-"tests/distributed/"}
COVERAGE_ENABLED=${COVERAGE_ENABLED:-"true"}

echo "配置："
echo "  USE_DOCKER: $USE_DOCKER"
echo "  TEST_PATTERN: $TEST_PATTERN"
echo "  COVERAGE: $COVERAGE_ENABLED"
echo ""

# 启动 Docker 集群（如果需要）
if [ "$USE_DOCKER" = "true" ] && [ "$DOCKER_AVAILABLE" = "true" ]; then
    echo -e "${YELLOW}[1/4] 启动 Docker 测试集群...${NC}"
    if [ -f "tests/distributed/scripts/start_cluster.sh" ]; then
        ./tests/distributed/scripts/start_cluster.sh
    else
        echo -e "${RED}错误: start_cluster.sh 不存在${NC}"
        exit 1
    fi
    echo ""
else
    echo -e "${YELLOW}[1/4] 跳过 Docker 集群启动（使用模拟模式）${NC}"
    echo ""
fi

# 运行测试
echo -e "${YELLOW}[2/4] 运行分布式测试...${NC}"

PYTEST_ARGS="-v --tb=short"

if [ "$COVERAGE_ENABLED" = "true" ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=src --cov-report=html --cov-report=term"
fi

echo "执行: pytest $PYTEST_ARGS $TEST_PATTERN"
echo ""

# 检查 pytest-cov
if [ "$COVERAGE_ENABLED" = "true" ] && ! python3 -c "import pytest_cov" 2>/dev/null; then
    echo -e "${YELLOW}警告: pytest-cov 未安装，跳过覆盖率${NC}"
    PYTEST_ARGS="-v --tb=short"
fi

# 运行测试
python3 -m pytest $PYTEST_ARGS "$TEST_PATTERN"
TEST_EXIT_CODE=$?

echo ""

# 收集日志
echo -e "${YELLOW}[3/4] 收集测试日志...${NC}"
LOG_DIR="logs/test_runs"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [ -f ".OneAgent/cluster_logs/" ]; then
    cp -r .OneAgent/cluster_logs/* "$LOG_DIR/" 2>/dev/null || true
    echo -e "${GREEN}✓ 集群日志已收集${NC}"
fi
echo ""

# 停止 Docker 集群（如果启动了）
if [ "$USE_DOCKER" = "true" ] && [ "$DOCKER_AVAILABLE" = "true" ]; then
    echo -e "${YELLOW}[4/4] 清理测试环境...${NC}"
    if [ -f "tests/distributed/scripts/stop_cluster.sh" ]; then
        ./tests/distributed/scripts/stop_cluster.sh
    fi
    echo ""
else
    echo -e "${YELLOW}[4/4] 测试环境使用模拟模式，无需清理${NC}"
    echo ""
fi

# 显示结果
echo -e "${GREEN}=== 测试完成 ===${NC}"
echo ""

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过${NC}"
    if [ "$COVERAGE_ENABLED" = "true" ] && [ -f "htmlcov/index.html" ]; then
        echo ""
        echo "覆盖率报告:"
        echo "  文件: ${PROJECT_ROOT}/htmlcov/index.html"
        echo "  打开: open htmlcov/index.html (macOS)"
        echo "  或: xdg-open htmlcov/index.html (Linux)"
    fi
    echo ""
else
    echo -e "${RED}✗ 测试失败 (退出码: $TEST_EXIT_CODE)${NC}"
    echo ""
    echo "请检查输出查看错误详情"
    echo ""
    if [ -d "logs/test_failures" ]; then
        echo "失败日志:"
        ls -lh logs/test_failures/
    fi
fi

exit $TEST_EXIT_CODE
