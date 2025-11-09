#!/bin/bash

#================================================================
# VUI Pro Panel - 一键安装脚本
# 
# 使用方法：
# curl -fsSL https://raw.githubusercontent.com/你的用户名/vui-pro-panel/main/install.sh | bash
#
# 或者：
# wget -O- https://raw.githubusercontent.com/你的用户名/vui-pro-panel/main/install.sh | bash
#================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# 版本和配置
VERSION="2.0.0"
GITHUB_REPO="jackyang1989/vui-pro-panel"  # 改成你的 GitHub 仓库
INSTALL_DIR="/opt/vui-pro"
ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-16)

# Logo
print_logo() {
    clear
    echo -e "${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   ██╗   ██╗██╗   ██╗██╗    ██████╗ ██████╗  ██████╗   ║
║   ██║   ██║██║   ██║██║    ██╔══██╗██╔══██╗██╔═══██╗  ║
║   ██║   ██║██║   ██║██║    ██████╔╝██████╔╝██║   ██║  ║
║   ╚██╗ ██╔╝██║   ██║██║    ██╔═══╝ ██╔══██╗██║   ██║  ║
║    ╚████╔╝ ╚██████╔╝██████╗██║     ██║  ██║╚██████╔╝  ║
║     ╚═══╝   ╚═════╝ ╚═════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝   ║
║                                                          ║
║            VUI Pro Panel v2.0.0                          ║
║         专业级 VPN 管理面板 - 一键安装                    ║
╚══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# 检查 root 权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}✗ 错误: 需要 root 权限运行此脚本${NC}"
        echo -e "${YELLOW}请使用: sudo bash $0${NC}"
        exit 1
    fi
}

# 检测系统
detect_system() {
    echo -e "${CYAN}[检测系统]${NC}"
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
        echo -e "${GREEN}✓ 检测到: $OS $VER${NC}"
    else
        echo -e "${RED}✗ 无法检测操作系统${NC}"
        exit 1
    fi
    
    if [[ ! "$OS" =~ ^(ubuntu|debian|centos|rhel)$ ]]; then
        echo -e "${RED}✗ 不支持的系统: $OS${NC}"
        echo -e "${YELLOW}支持: Ubuntu 20.04+, Debian 11+, CentOS 8+${NC}"
        exit 1
    fi
}

# 安装依赖
install_dependencies() {
    echo -e "${CYAN}[1/8] 安装系统依赖...${NC}"
    
    if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
        apt update -qq
        apt install -y curl wget git python3 python3-pip python3-venv nginx ufw >/dev/null 2>&1
    elif [[ "$OS" == "centos" || "$OS" == "rhel" ]]; then
        yum update -y -q
        yum install -y curl wget git python3 python3-pip nginx ufw >/dev/null 2>&1
    fi
    
    echo -e "${GREEN}✓ 系统依赖安装完成${NC}"
}

# 安装 Xray
install_xray() {
    echo -e "${CYAN}[2/8] 安装 Xray-core...${NC}"
    
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install >/dev/null 2>&1
    systemctl stop xray 2>/dev/null || true
    systemctl disable xray 2>/dev/null || true
    
    echo -e "${GREEN}✓ Xray-core 安装完成${NC}"
}

# 安装 Hysteria2
install_hysteria2() {
    echo -e "${CYAN}[3/8] 安装 Hysteria2...${NC}"
    
    bash <(curl -fsSL https://get.hy2.sh/) >/dev/null 2>&1 || true
    systemctl stop hysteria-server 2>/dev/null || true
    systemctl disable hysteria-server 2>/dev/null || true
    
    echo -e "${GREEN}✓ Hysteria2 安装完成${NC}"
}

# 配置 BBR
configure_bbr() {
    echo -e "${CYAN}[4/8] 配置 BBR 拥塞控制...${NC}"
    
    if ! grep -q "net.core.default_qdisc=fq" /etc/sysctl.conf; then
        cat >> /etc/sysctl.conf << 'EOF'

# BBR 拥塞控制优化
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
net.ipv4.tcp_rmem=8192 262144 536870912
net.ipv4.tcp_wmem=4096 16384 536870912
EOF
        sysctl -p >/dev/null 2>&1
    fi
    
    echo -e "${GREEN}✓ BBR 配置完成${NC}"
}

# 下载并安装后端
install_backend() {
    echo -e "${CYAN}[5/8] 安装后端服务...${NC}"
    
    # 创建目录
    mkdir -p $INSTALL_DIR/{backend,data,backups,logs}
    cd $INSTALL_DIR/backend
    
    # 下载代码
    echo -e "${YELLOW}从 GitHub 下载代码...${NC}"
    curl -fsSL "https://raw.githubusercontent.com/$GITHUB_REPO/main/backend/main.py" -o main.py
    curl -fsSL "https://raw.githubusercontent.com/$GITHUB_REPO/main/backend/requirements.txt" -o requirements.txt
    
    # 创建虚拟环境
    python3 -m venv venv
    source venv/bin/activate
    
    # 安装依赖
    echo -e "${YELLOW}安装 Python 依赖...${NC}"
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    
    deactivate
    
    echo -e "${GREEN}✓ 后端安装完成${NC}"
}

# 创建系统服务
create_service() {
    echo -e "${CYAN}[6/8] 创建系统服务...${NC}"
    
    cat > /etc/systemd/system/vui-pro.service << EOF
[Unit]
Description=VUI Pro Panel Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/backend/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="ADMIN_PASSWORD=$ADMIN_PASSWORD"
ExecStart=$INSTALL_DIR/backend/venv/bin/python main.py
Restart=on-failure
RestartSec=10s
StandardOutput=append:$INSTALL_DIR/logs/vui-pro.log
StandardError=append:$INSTALL_DIR/logs/vui-pro-error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable vui-pro
    systemctl start vui-pro
    
    echo -e "${GREEN}✓ 系统服务创建完成${NC}"
}

# 配置防火墙
configure_firewall() {
    echo -e "${CYAN}[7/8] 配置防火墙...${NC}"
    
    ufw allow 8000/tcp comment 'VUI Pro Panel' >/dev/null 2>&1
    ufw allow 80/tcp >/dev/null 2>&1
    ufw allow 443/tcp >/dev/null 2>&1
    ufw allow 8443/tcp >/dev/null 2>&1
    ufw --force enable >/dev/null 2>&1
    
    echo -e "${GREEN}✓ 防火墙配置完成${NC}"
}

# 健康检查
health_check() {
    echo -e "${CYAN}[8/8] 健康检查...${NC}"
    
    sleep 3
    
    if systemctl is-active --quiet vui-pro; then
        echo -e "${GREEN}✓ 服务运行正常${NC}"
    else
        echo -e "${RED}✗ 服务启动失败${NC}"
        echo -e "${YELLOW}查看日志: journalctl -u vui-pro -n 50${NC}"
    fi
    
    if curl -s http://localhost:8000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✓ API 健康检查通过${NC}"
    else
        echo -e "${YELLOW}⚠ API 暂时无响应，可能正在启动${NC}"
    fi
}

# 显示结果
show_result() {
    SERVER_IP=$(curl -s4 ifconfig.me || echo "127.0.0.1")
    
    clear
    print_logo
    
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}║                  🎉 安装成功！                           ║${NC}"
    echo -e "${GREEN}║                                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📱 面板访问信息${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}🌐 API 文档:${NC} ${BLUE}http://${SERVER_IP}:8000/docs${NC}"
    echo -e "  ${GREEN}🏠 主页:${NC} ${BLUE}http://${SERVER_IP}:8000${NC}"
    echo -e "  ${GREEN}❤️  健康检查:${NC} ${BLUE}http://${SERVER_IP}:8000/health${NC}"
    echo ""
    echo -e "  ${GREEN}👤 管理账号:${NC} ${YELLOW}admin${NC}"
    echo -e "  ${GREEN}🔑 管理密码:${NC} ${RED}${ADMIN_PASSWORD}${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}🛠️ 常用命令${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}启动:${NC} systemctl start vui-pro"
    echo -e "  ${GREEN}停止:${NC} systemctl stop vui-pro"
    echo -e "  ${GREEN}重启:${NC} systemctl restart vui-pro"
    echo -e "  ${GREEN}状态:${NC} systemctl status vui-pro"
    echo -e "  ${GREEN}日志:${NC} journalctl -u vui-pro -f"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}📂 安装信息${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${GREEN}安装目录:${NC} $INSTALL_DIR"
    echo -e "  ${GREEN}数据目录:${NC} $INSTALL_DIR/data"
    echo -e "  ${GREEN}日志目录:${NC} $INSTALL_DIR/logs"
    echo -e "  ${GREEN}备份目录:${NC} $INSTALL_DIR/backups"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}⚠️  重要提示${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${YELLOW}1. 请立即保存上面的管理员密码${NC}"
    echo -e "  ${YELLOW}2. 访问 API 文档开始使用面板${NC}"
    echo -e "  ${YELLOW}3. 建议配置域名和 SSL 证书${NC}"
    echo ""
    echo -e "${GREEN}感谢使用 VUI Pro Panel！${NC} 🚀"
    echo ""
    
    # 保存安装信息
    cat > $INSTALL_DIR/install_info.txt << INFO
VUI Pro Panel 安装信息
======================
安装时间: $(date '+%Y-%m-%d %H:%M:%S')
版本: $VERSION

访问地址: http://${SERVER_IP}:8000
API 文档: http://${SERVER_IP}:8000/docs
管理账号: admin
管理密码: ${ADMIN_PASSWORD}

安装目录: $INSTALL_DIR
配置目录: $INSTALL_DIR/backend
日志目录: $INSTALL_DIR/logs

常用命令:
systemctl start vui-pro    # 启动
systemctl stop vui-pro     # 停止  
systemctl restart vui-pro  # 重启
systemctl status vui-pro   # 状态
journalctl -u vui-pro -f   # 日志
INFO
    
    chmod 600 $INSTALL_DIR/install_info.txt
}

# 主函数
main() {
    print_logo
    
    echo -e "${YELLOW}准备安装 VUI Pro Panel v${VERSION}...${NC}"
    echo ""
    sleep 2
    
    check_root
    detect_system
    
    echo ""
    read -p "$(echo -e ${GREEN}"是否继续安装? [Y/n]: "${NC})" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
        echo -e "${YELLOW}安装已取消${NC}"
        exit 0
    fi
    
    echo ""
    echo -e "${GREEN}开始安装...${NC}"
    echo ""
    
    install_dependencies
    install_xray
    install_hysteria2
    configure_bbr
    install_backend
    create_service
    configure_firewall
    health_check
    
    sleep 2
    show_result
}

# 运行
main "$@"
