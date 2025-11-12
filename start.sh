#!/bin/bash

# ATLAS 快速启动脚本
# 使用方法：bash start.sh [dev|prod|test]

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 ATLAS 启动脚本${NC}"
echo ""

# 获取运行模式
MODE=${1:-dev}

case $MODE in
  dev)
    echo -e "${GREEN}📍 开发模式启动${NC}"
    
    # 检查依赖
    echo -e "${YELLOW}📦 检查 Python 依赖...${NC}"
    cd backend
    pip install -r requirements.txt > /dev/null 2>&1 || true
    
    # 启动后端
    echo -e "${YELLOW}🔧 启动后端 API (http://localhost:5000)...${NC}"
    python -m uvicorn app.main:app --reload --port 5000 &
    BACKEND_PID=$!
    
    cd ../frontend
    
    # 启动前端
    echo -e "${YELLOW}🎨 启动前端 (http://localhost:3000)...${NC}"
    npm install > /dev/null 2>&1 || true
    npm run dev &
    FRONTEND_PID=$!
    
    echo ""
    echo -e "${GREEN}✅ 应用已启动${NC}"
    echo -e "  后端 API: ${BLUE}http://localhost:5000${NC}"
    echo -e "  API 文档: ${BLUE}http://localhost:5000/docs${NC}"
    echo -e "  前端应用: ${BLUE}http://localhost:3000${NC}"
    echo -e "  默认账号: admin / admin123"
    echo ""
    echo -e "${YELLOW}⏹️  按 Ctrl+C 停止应用${NC}"
    
    # 等待进程
    wait
    ;;
    
  prod)
    echo -e "${GREEN}📍 生产模式启动${NC}"
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
      echo -e "${RED}❌ 未找到 Docker，请先安装 Docker${NC}"
      exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
      echo -e "${RED}❌ 未找到 docker-compose，请先安装 docker-compose${NC}"
      exit 1
    fi
    
    echo -e "${YELLOW}🐳 启动 Docker 容器...${NC}"
    docker-compose -f docker-compose.prod.yml up -d
    
    echo ""
    echo -e "${GREEN}✅ 生产容器已启动${NC}"
    echo -e "  前端应用: ${BLUE}http://localhost:3000${NC}"
    echo -e "  API 网关: ${BLUE}http://localhost${NC}"
    echo ""
    echo -e "${YELLOW}查看日志: docker-compose logs -f${NC}"
    ;;
    
  test)
    echo -e "${GREEN}📍 测试模式${NC}"
    
    # 运行测试
    echo -e "${YELLOW}🧪 运行测试套件...${NC}"
    cd backend
    
    # 安装依赖
    pip install -r requirements.txt > /dev/null 2>&1 || true
    
    # 运行所有测试
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "认证测试"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pytest tests/test_auth.py -v --tb=short || true
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "服务测试"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pytest tests/test_services.py -v --tb=short || true
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "用户测试"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pytest tests/test_users.py -v --tb=short || true
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "修复验证测试"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    pytest tests/test_fixes.py -v --tb=short || true
    
    echo ""
    echo -e "${GREEN}✅ 测试完成${NC}"
    ;;
    
  *)
    echo -e "${RED}❌ 未知模式: $MODE${NC}"
    echo ""
    echo "用法: $0 [dev|prod|test]"
    echo ""
    echo "  dev   - 开发模式（本地运行）"
    echo "  prod  - 生产模式（Docker）"
    echo "  test  - 运行测试套件"
    exit 1
    ;;
esac
