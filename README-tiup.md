# 使用TiUP部署TiDB集群

本文档提供使用TiUP工具部署TiDB集群(含TiFlash)的操作指南。

## 环境要求

- 操作系统: Linux (CentOS 7+, Ubuntu 16.04+)
- 内存: 至少16GB RAM
- 磁盘: 至少100GB可用空间
- 网络: 所有节点之间网络互通，集群内网络延迟低
- 用户权限: 具有sudo或root权限

## Mac系统说明

Mac系统不支持TiUP的集群部署功能，但可以通过以下方式运行TiDB：

1. **使用修改版脚本**：我们已修改`deploy-tidb-tiflash.sh`脚本，使其在检测到Mac系统时自动使用TiUP Playground模式部署单机演示环境。

2. **手动使用Playground**：
   ```bash
   # 安装TiUP
   curl --proto '=https' --tlsv1.2 -sSf https://tiup-mirrors.pingcap.com/install.sh | sh
   source ~/.zshrc  # 或 source ~/.bash_profile
   
   # 启动包含TiFlash的本地playground
   tiup playground --db 1 --pd 1 --kv 1 --tiflash 1
   ```

3. **使用Docker**：
   ```bash
   docker pull pingcap/tidb:latest
   docker run -p 4000:4000 pingcap/tidb:latest
   ```
   
   注意：Docker模式不包含TiFlash组件

4. **使用虚拟机**：在Mac上安装Linux虚拟机并在其中运行完整的部署脚本

## 快速部署

我们提供了一键部署脚本`deploy-tidb-tiflash.sh`，可以在单机环境下快速部署一个测试用的TiDB集群。

### 使用步骤

1. 赋予脚本执行权限:

```bash
chmod +x deploy-tidb-tiflash.sh
```

2. 执行脚本:

```bash
./deploy-tidb-tiflash.sh
```

脚本将自动:
- 安装TiUP工具
- 创建拓扑配置文件
- 部署TiDB集群
- 启动集群
- 检查集群状态

### 集群访问

部署完成后，可通过以下方式访问集群:

- **TiDB**: 默认端口4000，用户名root，无密码
  ```
  mysql -h <主机IP> -P 4000 -u root
  ```

- **Grafana**: 浏览器访问 `http://<主机IP>:3000`，用户名和密码均为admin

## TiFlash使用

TiFlash是TiDB的分析引擎，提供了HTAP能力。部署完成后，需要执行以下步骤来使用TiFlash:

1. 验证TiFlash状态:

```sql
SELECT * FROM information_schema.tiflash_replica;
```

2. 为表设置TiFlash副本:

```sql
ALTER TABLE <数据库名>.<表名> SET TIFLASH REPLICA 1;
```

3. 确认同步状态:

```sql
SELECT * FROM information_schema.tiflash_replica WHERE TABLE_SCHEMA = '<数据库名>' AND TABLE_NAME = '<表名>';
```

当`AVAILABLE`字段为1时，表示TiFlash副本可用。

4. 使用TiFlash进行分析查询:

```sql
SET @@session.tidb_isolation_read_engines='tiflash'; -- 强制使用TiFlash引擎
SELECT COUNT(*) FROM <表名>;
```

## 常用管理命令

```bash
# 查看集群状态
tiup cluster display tidb-cluster

# 启动集群
tiup cluster start tidb-cluster

# 停止集群
tiup cluster stop tidb-cluster

# 重启集群
tiup cluster restart tidb-cluster

# 扩展集群
tiup cluster scale-out tidb-cluster scale-out.yaml --user root

# 升级集群
tiup cluster upgrade tidb-cluster v7.6.0

# 销毁集群
tiup cluster destroy tidb-cluster
```

## 配置定制

如需更复杂的部署配置，可以编辑`topology.yaml`文件，添加更多节点或调整参数。

## 常见问题

1. **端口被占用**：确保相关端口未被其他服务占用，特别是4000、2379、20160、3930等端口。

2. **内存不足**：最小化安装时，TiDB+PD+TiKV+TiFlash至少需要16GB内存，建议生产环境至少32GB。

3. **TiFlash同步失败**：检查TiFlash日志中是否有错误信息，可通过命令访问:
   ```
   tiup cluster log tidb-cluster --include tiflash
   ```

4. **SSH连接问题**：确保所有节点间可以通过SSH密钥免密登录。

## 更多资源

- [TiDB文档中心](https://docs.pingcap.com/zh/tidb/stable)
- [TiUP参考手册](https://docs.pingcap.com/zh/tidb/stable/tiup-reference)
- [TiFlash文档](https://docs.pingcap.com/zh/tidb/stable/tiflash-overview) 