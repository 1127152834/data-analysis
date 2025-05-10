# AutoFlow (tidb-ai) 源码部署指南

本文档提供了从源码部署 AutoFlow 项目的详细步骤和注意事项。

## 一、环境要求

### 1.1 基础系统要求

- **操作系统**: Linux, macOS, 或 Windows (通过WSL2)
- **内存**: 最低8GB，推荐16GB以上
- **CPU**: 最低4核，推荐8核以上
- **磁盘空间**: 最低20GB可用空间

### 1.2 必要软件

- **Docker**: 20.10.0 或更高版本
- **Docker Compose**: V2 或更高版本
- **Git**: 任意最新版本
- **TiDB数据库**:
  - 推荐使用 [TiDB Cloud Serverless](https://tidbcloud.com/)
  - 或自建 TiDB 集群 (>= v8.4)

### 1.3 开发环境工具（可选）

如果需要进行代码开发或调试，还需要：

- **Node.js**: 18.x 或更高版本
- **pnpm**: 8.x 或更高版本
- **Python**: 3.11 或更高版本
- **uv**: 用于Python依赖管理

## 二、源码获取与准备

### 2.1 克隆代码仓库

```bash
git clone https://github.com/pingcap/autoflow.git
cd autoflow
# 如果您已将项目重命名为tidb-ai
# git clone <您的仓库地址> tidb-ai
# cd tidb-ai
```

### 2.2 创建环境变量配置

首先需要创建项目的环境变量文件：

```bash
# 假设项目中包含.env.example文件
cp .env.example .env
```

如果没有.env.example文件，请手动创建一个.env文件，包含以下必要配置：

```
# 随机生成的安全密钥
SECRET_KEY=your_random_secret_key

# TiDB数据库连接配置
TIDB_HOST=your-tidb-host
TIDB_PORT=4000
TIDB_USER=your-tidb-user
TIDB_PASSWORD=your-tidb-password
TIDB_DATABASE=your-database-name
TIDB_SSL=true

# 推荐使用 TiDB Cloud Serverless

# LLM模型配置
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your-llm-api-key
LLM_MODEL=gpt-3.5-turbo

# 嵌入模型设置
EMBEDDING_API_BASE=https://api.openai.com/v1
EMBEDDING_API_KEY=your-embedding-api-key
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_MAX_TOKENS=8191

# 其他配置
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=
```

生成随机安全密钥：

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.3 TiDB数据库设置

1. 创建TiDB数据库
   - 使用TiDB Cloud Serverless，创建一个新的数据库
   - 或使用现有TiDB集群创建新的数据库

2. 获取数据库连接信息并填入.env文件
   - 主机地址 (TIDB_HOST)
   - 端口 (TIDB_PORT)
   - 用户名 (TIDB_USER)
   - 密码 (TIDB_PASSWORD)
   - 数据库名 (TIDB_DATABASE)
   - SSL设置 (TIDB_SSL)：TiDB Cloud需设为true，自建集群可根据配置设置

## 三、Docker部署步骤

### 3.1 数据库初始化

运行数据库迁移命令，创建所需的表结构：

```bash
docker compose run backend /bin/sh -c "alembic upgrade head"
```

### 3.2 创建管理员账户

初始化系统并创建默认管理员账户：

```bash
# 使用默认设置（随机密码）
docker compose run backend /bin/sh -c "python bootstrap.py"

# 指定管理员邮箱
docker compose run backend /bin/sh -c "python bootstrap.py --email admin@example.com"

# 同时指定密码
docker compose run backend /bin/sh -c "python bootstrap.py --email admin@aolei.com --password Admin@123"
```

输出中会显示生成的管理员账户和密码，请妥善保存。

### 3.3 启动服务

根据网络环境选择合适的启动命令：

**标准环境 (国际网络环境)**:

```bash
# 不使用本地embedding模型
docker compose up -d

# 使用本地embedding模型
docker compose --profile local-embedding-reranker up -d
```

**中国网络环境**:

```bash
# 不使用本地embedding模型
docker compose -f docker-compose-cn.yml up -d

# 使用本地embedding模型
docker compose -f docker-compose-cn.yml --profile local-embedding-reranker up -d
```

**开发环境**:

```bash
docker compose -f docker-compose.dev.yml up -d
```

### 3.4 验证服务状态

检查容器运行状态：

```bash
docker compose ps
```

所有服务应显示为"running"状态。

访问前端界面：

```
http://localhost:3000
```

访问后端API文档：

```
http://localhost:8000/docs
```

## 四、系统初始化配置

成功部署后，需要进行以下初始化配置：

### 4.1 登录管理后台

使用前面创建的管理员账户登录系统：

```
http://localhost:3000/admin
```

### 4.2 配置LLM模型

1. 进入管理后台中的"Models > LLMs"页面
2. 添加或配置默认LLM模型
3. 常用选项包括OpenAI、Azure、本地模型等

### 4.3 配置Embedding模型

1. 进入"Models > Embedding Models"页面
2. 添加或配置默认Embedding模型
3. 选项包括OpenAI、Local、HuggingFace等

### 4.4 创建知识库

1. 进入"Knowledge Bases"页面
2. 点击"Add Knowledge Base"创建新知识库
3. 配置知识库名称和描述
4. 选择上传文档或设置网站爬虫

### 4.5 配置聊天引擎

1. 进入"Chat Engines"页面
2. 创建或编辑默认聊天引擎
3. 关联到创建的知识库
4. 设置检索参数和提示模板

## 五、配置定制与优化

### 5.1 调整容器资源

如果运行环境资源有限，可以调整docker-compose.yml中的资源限制：

```yaml
services:
  backend:
    # ...
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### 5.2 使用本地Embedding模型

对于不便使用云端模型的情况，可以启用本地Embedding模型服务：

```bash
docker compose --profile local-embedding-reranker up -d
```

然后在管理后台中配置Embedding模型的URL为：

```
http://local-embedding-reranker:5001
```

### 5.3 TiDB数据库优化

如果使用自建TiDB集群，建议进行以下优化：

1. 为向量检索创建合适的索引
2. 调整TiDB参数适应向量搜索负载
3. 定期执行vacuum和分析以维护性能

## 六、常见问题与解决方案

### 6.1 服务启动失败

**问题**: 运行`docker compose up`后部分服务启动失败

**解决方案**:
1. 检查日志：`docker compose logs -f <service_name>`
2. 确认TiDB连接是否正确
3. 验证环境变量配置
4. 确保端口未被占用：`lsof -i :3000` 或 `lsof -i :8000`

### 6.2 数据库连接问题

**问题**: 后端服务连接不到TiDB数据库

**解决方案**:
1. 确认TiDB服务是否可访问：`telnet <TIDB_HOST> <TIDB_PORT>`
2. 检查连接参数是否正确
3. 如使用TiDB Cloud，确认IP允许列表是否包含您的部署环境IP
4. 检查SSL设置是否正确

### 6.3 LLM API连接问题

**问题**: 无法连接到LLM API服务

**解决方案**:
1. 确认API密钥是否有效
2. 验证网络环境是否可访问API服务
3. 在中国环境下使用可替代的模型提供商
4. 考虑使用代理服务

### 6.4 文件上传限制

**问题**: 上传大文件时失败

**解决方案**:
1. 调整Nginx/代理服务器的上传限制
2. 修改docker-compose.yml中的相关配置
3. 将大文件分割成较小的块

## 七、系统更新与维护

### 7.1 更新系统版本

从GitHub获取最新代码并重新部署：

```bash
# 获取最新代码
git pull origin main

# 构建并重启服务
docker compose down
docker compose build
docker compose up -d
```

### 7.2 数据库备份与恢复

定期备份TiDB数据：

```bash
# 使用TiDB提供的备份工具
# 或使用标准SQL导出
mysqldump -h <TIDB_HOST> -P <TIDB_PORT> -u <TIDB_USER> -p <TIDB_DATABASE> > backup.sql
```

恢复数据：

```bash
mysql -h <TIDB_HOST> -P <TIDB_PORT> -u <TIDB_USER> -p <TIDB_DATABASE> < backup.sql
```

### 7.3 日志管理

查看服务日志：

```bash
# 查看特定服务的日志
docker compose logs -f backend

# 查看所有服务的日志
docker compose logs -f
```

日志轮换配置在docker-compose.yml中已设置：

```yaml
logging:
  driver: json-file
  options:
    max-size: "50m"
    max-file: "6"
```

## 八、从源码构建镜像（可选）

如需自定义修改代码后构建镜像，可按以下步骤操作：

### 8.1 构建后端镜像

```bash
cd backend
docker build -t autoflow-backend:custom .
```

### 8.2 构建前端镜像

```bash
cd frontend
docker build -t autoflow-frontend:custom .
```

### 8.3 使用自定义镜像

修改docker-compose.yml文件，使用自定义镜像：

```yaml
services:
  backend:
    image: autoflow-backend:custom
    # ...
  
  frontend:
    image: autoflow-frontend:custom
    # ...

  background:
    image: autoflow-backend:custom
    # ...
```

## 九、本地开发环境搭建（可选）

如需进行代码开发和调试，建议设置本地开发环境：

### 9.1 后端开发环境

```bash
cd backend

# 使用uv创建虚拟环境
uv venv

# 激活虚拟环境
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

# 安装依赖
uv pip install -e .
```

### 9.2 前端开发环境

```bash
cd frontend/app

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

### 9.3 使用开发模式启动

使用docker-compose.dev.yml配置进行开发，它会将本地代码目录挂载到容器中：

```bash
docker compose -f docker-compose.dev.yml up -d
```

## 十、生产环境部署建议

### 10.1 安全考虑

- 使用反向代理（如Nginx）保护服务
- 配置HTTPS
- 限制管理后台访问IP
- 定期更新密码和API密钥

### 10.2 高可用性配置

- 使用容器编排工具（如Kubernetes）
- 设置服务自动恢复
- 实施监控和告警

### 10.3 性能优化

- 使用CDN加速静态资源
- 调整TiDB参数以优化向量查询
- 为高负载场景增加资源分配 