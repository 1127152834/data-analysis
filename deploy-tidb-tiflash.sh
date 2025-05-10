#!/bin/bash

# 部署TiDB集群（含TiFlash）的脚本
# 此脚本使用TiUP来部署单机版TiDB集群，适用于测试环境

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# 获取当前主机IP，兼容Mac和Linux
get_host_ip() {
    os=$(uname)
    if [[ "$os" == "Darwin" ]]; then
        # Mac系统获取IP
        HOST_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -n 1)
    else
        # Linux系统获取IP
        HOST_IP=$(ip route get 1 | awk '{print $7;exit}' 2>/dev/null || hostname -I | awk '{print $1}')
    fi
    
    # 如果上述方法都失败，使用localhost
    if [[ -z "$HOST_IP" ]]; then
        HOST_IP="127.0.0.1"
        echo -e "${YELLOW}警告: 无法自动获取IP地址，使用默认值 ${HOST_IP}${NC}"
    fi
}

# 获取IP地址
get_host_ip
echo -e "${GREEN}当前主机IP: ${HOST_IP}${NC}"

# 安装TiUP
if ! command -v tiup &> /dev/null; then
    echo -e "${YELLOW}TiUP未安装，正在安装...${NC}"
    curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
    
    # 根据不同Shell添加环境变量
    if [[ "$os" == "Darwin" ]]; then
        # Mac通常使用zsh或bash
        if [[ -f "$HOME/.zshrc" ]]; then
            source ~/.zshrc
        else
            source ~/.bash_profile
        fi
    else
        # Linux通常使用bash
        source ~/.profile
    fi
    
    echo -e "${GREEN}TiUP安装完成${NC}"
else
    echo -e "${GREEN}TiUP已安装${NC}"
fi

# 确保TiUP集群组件已安装
if ! tiup cluster version &> /dev/null; then
    echo -e "${YELLOW}安装TiUP集群组件...${NC}"
    tiup cluster
    echo -e "${GREEN}TiUP集群组件安装完成${NC}"
fi

# Mac系统使用playground部署
if [[ "$(uname)" == "Darwin" ]]; then
    echo -e "${YELLOW}检测到Mac系统，将使用playground模式部署...${NC}"
    echo -e "${YELLOW}是否继续? [Y/n]${NC}"
    read -r answer
    if [[ "$answer" =~ ^[Nn]$ ]]; then
        echo -e "${RED}部署已取消${NC}"
        exit 0
    fi
    
    echo -e "${YELLOW}启动TiDB playground (包含TiFlash)...${NC}"
    tiup playground --db 1 --pd 1 --kv 1 --tiflash 1
    exit 0
fi

# 以下是Linux系统使用集群模式部署的代码
# 创建集群拓扑配置文件
echo -e "${YELLOW}创建集群拓扑配置文件...${NC}"
cat > topology.yaml << EOF
global:
  user: "tidb"
  ssh_port: 22
  deploy_dir: "/tidb-deploy"
  data_dir: "/tidb-data"

server_configs:
  tidb:
    log.slow-threshold: 300
  tikv:
    readpool.storage.use-unified-pool: false
    readpool.coprocessor.use-unified-pool: true
  pd:
    replication.enable-placement-rules: true
    replication.location-labels: ["host"]

pd_servers:
  - host: ${HOST_IP}
    
tikv_servers:
  - host: ${HOST_IP}
    port: 20160
    status_port: 20180
    config:
      server.labels: { host: "tikv1" }

tidb_servers:
  - host: ${HOST_IP}
    port: 4000
    status_port: 10080

tiflash_servers:
  - host: ${HOST_IP}
    tcp_port: 9000
    http_port: 8123
    flash_service_port: 3930
    flash_proxy_port: 20170
    flash_proxy_status_port: 20292
    metrics_port: 8234
    config:
      logger.level: "info"
      
monitoring_servers:
  - host: ${HOST_IP}
    
grafana_servers:
  - host: ${HOST_IP}
    
alertmanager_servers:
  - host: ${HOST_IP}
EOF

echo -e "${GREEN}拓扑配置文件已创建: topology.yaml${NC}"

# 集群名称
CLUSTER_NAME="tidb-cluster"

# 检查集群是否已存在
if tiup cluster list | grep -q ${CLUSTER_NAME}; then
    echo -e "${YELLOW}集群 ${CLUSTER_NAME} 已存在，是否销毁并重新部署? [y/N]${NC}"
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo -e "${RED}销毁已有集群...${NC}"
        tiup cluster destroy ${CLUSTER_NAME} -y
    else
        echo -e "${YELLOW}部署已取消${NC}"
        exit 0
    fi
fi

# 检查拓扑配置
echo -e "${YELLOW}检查拓扑配置...${NC}"
tiup cluster check topology.yaml --user root

# 修复拓扑配置的问题（如果有）
echo -e "${YELLOW}修复拓扑配置问题...${NC}"
tiup cluster check topology.yaml --user root --apply

# 部署集群
echo -e "${YELLOW}开始部署集群...${NC}"
tiup cluster deploy ${CLUSTER_NAME} v7.5.1 topology.yaml --user root -y

# 启动集群
echo -e "${YELLOW}启动集群...${NC}"
tiup cluster start ${CLUSTER_NAME}

# 检查集群状态
echo -e "${YELLOW}检查集群状态...${NC}"
tiup cluster display ${CLUSTER_NAME}

echo -e "${GREEN}===============================================${NC}"
echo -e "${GREEN}TiDB集群已成功部署！${NC}"
echo -e "${GREEN}集群名称: ${CLUSTER_NAME}${NC}"
echo -e "${GREEN}TiDB访问地址: ${HOST_IP}:4000${NC}"
echo -e "${GREEN}Grafana访问地址: http://${HOST_IP}:3000 (用户名:admin, 密码:admin)${NC}"
echo -e "${GREEN}===============================================${NC}"
echo -e "${YELLOW}提示: 请确保防火墙允许相关端口访问${NC}"
echo -e "${YELLOW}要管理集群，请使用以下命令:${NC}"
echo -e "${YELLOW}  - 查看集群: tiup cluster display ${CLUSTER_NAME}${NC}"
echo -e "${YELLOW}  - 启动集群: tiup cluster start ${CLUSTER_NAME}${NC}"
echo -e "${YELLOW}  - 停止集群: tiup cluster stop ${CLUSTER_NAME}${NC}"
echo -e "${YELLOW}  - 销毁集群: tiup cluster destroy ${CLUSTER_NAME}${NC}"
echo -e "${YELLOW}  - 扩展集群: tiup cluster scale-out ${CLUSTER_NAME} scale-out.yaml --user root${NC}"

# 检测MySQL客户端并提供连接命令
if command -v mysql &> /dev/null; then
    echo -e "${GREEN}可以使用以下命令连接到TiDB:${NC}"
    echo -e "${GREEN}  mysql -h ${HOST_IP} -P 4000 -u root${NC}"
else
    echo -e "${YELLOW}未检测到MySQL客户端，请安装后使用以下命令连接TiDB:${NC}"
    echo -e "${YELLOW}  mysql -h ${HOST_IP} -P 4000 -u root${NC}"
fi

# 提供查看TiFlash同步状态的SQL
echo -e "${GREEN}TiFlash部署完成后，可以通过以下SQL查看同步状态:${NC}"
echo -e "${GREEN}  SELECT * FROM information_schema.tiflash_replica;${NC}"
echo -e "${GREEN}要将某个表同步到TiFlash，请执行:${NC}"
echo -e "${GREEN}  ALTER TABLE 数据库名.表名 SET TIFLASH REPLICA 1;${NC}" 