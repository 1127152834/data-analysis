# AutoFlow 后端技术文档

## 1. 项目概述

AutoFlow 后端服务是一个基于 FastAPI 构建的 AI 驱动的知识库和聊天系统。该系统使用检索增强生成（RAG）技术将大型语言模型（LLM）与知识库相结合，提供准确且有上下文的回答。

### 核心功能

- **知识库管理**：创建和管理知识库，包括文档上传、处理和索引
- **向量检索**：使用 TiDB 向量存储进行高效的相似性搜索
- **LLM 集成**：支持多种大型语言模型（如OpenAI、Azure、Google等）
- **聊天引擎**：可配置的聊天系统，支持上下文保留和知识检索
- **用户认证**：完整的用户管理和认证系统
- **评估系统**：对模型响应质量的评估功能

### 技术栈

- **Web 框架**：FastAPI
- **数据库**：TiDB (SQL + 向量存储)
- **异步任务**：Celery + Redis
- **用户认证**：FastAPI Users
- **嵌入/向量模型**：多种嵌入模型支持
- **LLM 集成**：支持多种 LLM 提供商

## 2. 系统架构

```
┌─────────────────────────────────────┐
│               前端应用              │
└───────────────┬─────────────────────┘
                │ HTTP/WebSocket
┌───────────────▼─────────────────────┐
│            FastAPI 应用             │
│                                     │
│  ┌─────────┐ ┌──────────┐ ┌───────┐ │
│  │API 路由 │ │中间件    │ │认证   │ │
│  └─────────┘ └──────────┘ └───────┘ │
└───────────────┬─────────────────────┘
                │
┌───────────────▼─────────────────────┐
│               核心服务              │
│                                     │
│ ┌──────────┐ ┌──────────┐ ┌───────┐ │
│ │ RAG 引擎 │ │知识库管理│ │聊天   │ │
│ └──────────┘ └──────────┘ └───────┘ │
└───────────────┬─────────────────────┘
                │
┌───────────────▼─────────────────────┐
│               数据层                │
│                                     │
│ ┌──────────┐ ┌──────────┐ ┌───────┐ │
│ │TiDB (SQL)│ │向量存储  │ │Redis  │ │
│ └──────────┘ └──────────┘ └───────┘ │
└─────────────────────────────────────┘
```

### 主要组件

1. **API 层**：处理 HTTP 请求，路由和响应
2. **认证系统**：用户管理、权限和 API 密钥
3. **RAG 引擎**：检索增强生成核心
4. **知识库管理**：文档处理、分块和索引
5. **LLM 集成**：连接和管理各种语言模型
6. **异步任务系统**：管理长时间运行的任务
7. **数据存储**：SQL 和向量数据管理

## 3. 项目结构

```
backend/
├── app/                   # 主应用程序
│   ├── alembic/           # 数据库迁移
│   ├── api/               # API 路由和端点
│   │   ├── admin_routes/  # 管理员 API
│   │   └── routes/        # 用户 API
│   ├── auth/              # 认证功能
│   ├── core/              # 核心配置
│   ├── evaluation/        # 评估系统
│   ├── file_storage/      # 文件存储
│   ├── models/            # 数据模型
│   ├── rag/               # 检索增强生成
│   │   ├── chat/          # 聊天功能
│   │   ├── embeddings/    # 嵌入模型
│   │   ├── knowledge_base/# 知识库管理
│   │   ├── llms/          # LLM 集成
│   │   └── retrievers/    # 检索器
│   ├── repositories/      # 数据访问层
│   ├── tasks/             # 异步任务
│   └── utils/             # 实用工具
├── local_embedding_reranker/  # 本地嵌入和重排模型
├── tests/                     # 测试
└── alembic.ini                # 数据库迁移配置
```

## 4. 核心模块详解

### 4.1 API 模块 (`app/api/`)

API 模块处理所有的请求路由和端点，分为用户 API 和管理员 API。

#### 主要 API 路由：

- **聊天 API**：处理对话和消息
- **知识库 API**：管理知识库资源
- **认证 API**：用户登录、注册和令牌
- **文档 API**：文档上传和检索
- **管理员 API**：系统配置和监控

#### 示例端点：

- `/api/v1/chat/` - 管理聊天会话
- `/api/v1/chat/{chat_id}/message` - 发送新消息
- `/api/v1/documents/` - 文档管理
- `/api/v1/auth/login` - 用户登录

### 4.2 RAG 系统 (`app/rag/`)

RAG（检索增强生成）是系统的核心，将知识库检索与语言模型生成相结合。

#### 主要组件：

- **检索器**：从知识库检索相关文档
- **嵌入模型**：将文本转换为向量表示
- **LLM 集成**：连接各种语言模型
- **重排器**：优化检索结果的排序
- **知识库管理**：管理文档和索引

### 4.3 数据模型 (`app/models/`)

定义系统中使用的所有数据模型。

#### 主要模型：

- **用户模型**：用户信息和权限
- **聊天模型**：聊天会话和消息
- **知识库模型**：知识库和文档
- **文档模型**：文档元数据和内容
- **块模型**：文档的块
- **LLM 模型**：语言模型配置
- **嵌入模型**：嵌入模型配置

### 4.4 认证系统 (`app/auth/`)

处理用户认证和授权。

#### 功能：

- 用户注册和登录
- JWT 令牌管理
- 权限控制
- API 密钥管理

### 4.5 异步任务 (`app/tasks/`)

使用 Celery 管理长时间运行的任务。

#### 主要任务：

- 文档处理和索引
- 网站爬取
- 发送电子邮件
- 数据导出
- 定期维护

### 4.6 评估系统 (`app/evaluation/`)

评估 RAG 系统和 LLM 响应的质量。

#### 功能：

- 运行评估任务
- 比较不同模型的性能
- 生成评估报告
- 提供评估指标

## 5. 安装与配置

### 5.1 环境要求

- Python 3.9 或更高版本
- TiDB 数据库
- Redis 服务器
- 足够的存储空间用于文档和向量

### 5.2 快速开始

1. 克隆存储库：

```bash
git clone https://github.com/your-repo/data-analysis.git
cd data-analysis/backend
```

2. 安装依赖：

```bash
# 安装 uv 工具
pip install uv

# 使用 uv 安装依赖
uv sync
```

3. 配置环境变量：

```bash
cp .env.example .env
# 编辑 .env 文件设置环境变量
```

4. 运行数据库迁移：

```bash
make migrate
```

5. 启动开发服务器：

```bash
uv run python main.py runserver
```

### 5.3 Docker 部署

使用 Docker 部署：

```bash
# 构建镜像
docker build -t autoflow-backend .

# 运行容器
docker run -p 8000:8000 --env-file .env autoflow-backend
```

### 5.4 关键配置项

`.env` 文件中的主要配置：

```
# 数据库连接
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USER=root
TIDB_PASSWORD=password
TIDB_DATABASE=autoflow

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379

# LLM配置
LLM_API_BASE=https://api.openai.com/v1
LLM_API_KEY=your_api_key
LLM_MODEL=gpt-3.5-turbo

# 嵌入模型
EMBEDDING_API_BASE=https://api.openai.com/v1
EMBEDDING_API_KEY=your_api_key
EMBEDDING_MODEL=text-embedding-ada-002

# 安全设置
SECRET_KEY=your_secret_key
```

## 6. API 接口详解

### 6.1 聊天 API

#### 创建聊天会话

```
POST /api/v1/chat/
```

请求体：
```json
{
  "title": "新对话",
  "chat_engine_id": "default"
}
```

响应：
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "title": "新对话",
  "created_at": "2023-07-01T12:00:00Z",
  "chat_engine_id": "default"
}
```

#### 发送消息

```
POST /api/v1/chat/{chat_id}/message
```

请求体：
```json
{
  "content": "什么是 TiDB？"
}
```

响应：
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "chat_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "role": "assistant",
  "content": "TiDB 是一个开源的分布式 SQL 数据库...",
  "created_at": "2023-07-01T12:01:00Z",
  "sources": [
    {
      "document_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "chunk_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "content": "TiDB 是一个开源的分布式...",
      "score": 0.92
    }
  ]
}
```

### 6.2 知识库 API

#### 创建知识库

```
POST /api/v1/admin/knowledge_base/
```

请求体：
```json
{
  "name": "TiDB 文档",
  "description": "TiDB 产品文档"
}
```

响应：
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "TiDB 文档",
  "description": "TiDB 产品文档",
  "created_at": "2023-07-01T12:00:00Z"
}
```

#### 上传文档

```
POST /api/v1/admin/knowledge_base/{kb_id}/document/
```

表单数据：
- `file`: 文件
- `metadata`: JSON 元数据

响应：
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "knowledge_base_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "tidb_intro.pdf",
  "status": "processing",
  "created_at": "2023-07-01T12:05:00Z"
}
```

### 6.3 用户认证 API

#### 用户注册

```
POST /api/v1/auth/register
```

请求体：
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "name": "Test User"
}
```

响应：
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "email": "user@example.com",
  "name": "Test User",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2023-07-01T12:00:00Z"
}
```

#### 用户登录

```
POST /api/v1/auth/login
```

请求体：
```json
{
  "username": "user@example.com",
  "password": "securepassword"
}
```

响应：
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

## 7. 开发指南

### 7.1 添加新 API 端点

1. 在 `app/api/routes/` 目录中创建新路由文件
2. 定义路由和处理函数
3. 在 `app/api/main.py` 中注册路由

示例：

```python
# app/api/routes/custom.py
from fastapi import APIRouter, Depends
from app.models.user import User
from app.auth.users import current_active_user

router = APIRouter(prefix="/custom", tags=["custom"])

@router.get("/")
async def get_custom_data(current_user: User = Depends(current_active_user)):
    return {"message": "Custom data"}
```

注册路由：

```python
# app/api/main.py
from app.api.routes import custom

api_router.include_router(custom.router, tags=["custom"])
```

### 7.2 创建新模型

1. 在 `app/models/` 目录中创建新模型文件
2. 定义 SQLModel 类
3. 创建 Alembic 迁移

示例：

```python
# app/models/custom.py
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel
from uuid import UUID, uuid4

class CustomModel(SQLModel, table=True):
    __tablename__ = "custom_models"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: UUID = Field(foreign_key="users.id")
```

创建迁移：

```bash
alembic revision --autogenerate -m "Add custom model"
alembic upgrade head
```

### 7.3 集成新的 LLM 提供商

1. 在 `app/rag/llms/` 目录中创建新的 LLM 连接器
2. 实现必要的接口方法
3. 在 LLM 工厂中注册新提供商

### 7.4 添加新的嵌入模型

1. 在 `app/rag/embeddings/` 目录中创建新的嵌入模型连接器
2. 实现必要的接口方法
3. 在嵌入模型工厂中注册新提供商

## 8. 最佳实践

### 8.1 代码规范

- 使用类型注解
- 遵循 PEP 8 风格指南
- 使用异步函数处理 I/O 操作
- 编写单元测试

### 8.2 性能优化

- 使用异步请求并行处理
- 实现缓存策略
- 索引频繁查询的数据库字段
- 监控慢查询

### 8.3 安全考虑

- 保护 API 密钥和敏感信息
- 设置合适的 CORS 策略
- 使用 HTTPS
- 限制资源访问

### 8.4 测试策略

- 编写单元测试验证功能
- 进行集成测试验证组件交互
- 执行性能测试识别瓶颈
- 实现持续集成

## 9. 故障排除

### 9.1 常见问题

#### 数据库连接问题

**症状**：应用程序无法连接到 TiDB。

**解决方案**：
- 检查 TiDB 连接参数
- 确认 TiDB 服务正在运行
- 验证网络连接和防火墙设置

#### LLM API 错误

**症状**：无法连接到 LLM 服务。

**解决方案**：
- 验证 API 密钥是否有效
- 检查是否超过 API 限制
- 确认网络连接畅通

#### 文档处理失败

**症状**：文档上传后无法处理或索引。

**解决方案**：
- 检查 Celery 工作进程
- 验证文件格式是否受支持
- 查看任务日志获取详细错误

### 9.2 日志记录

系统日志位于：

- 应用程序日志：由 uvicorn 输出到标准输出
- Celery 任务日志：在 Celery 工作进程输出
- 错误追踪：如果配置了 Sentry，可在 Sentry 仪表板查看

### 9.3 调试技巧

- 启用调试模式运行服务器：`uvicorn app.api_server:app --reload --debug`
- 使用 FastAPI 的自动文档：访问 `/docs` 或 `/redoc` 端点
- 检查数据库查询：增加日志或使用数据库监控工具

## 10. API参考

完整的 API 文档可在运行服务器后通过访问以下地址获取：

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`

这些自动生成的文档提供了所有 API 端点的详细说明、请求参数和响应格式。

---

## 附录A：环境变量参考

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `TIDB_HOST` | TiDB 服务器主机名 | localhost |
| `TIDB_PORT` | TiDB 服务器端口 | 4000 |
| `TIDB_USER` | TiDB 用户名 | root |
| `TIDB_PASSWORD` | TiDB 密码 | password |
| `TIDB_DATABASE` | TiDB 数据库名称 | autoflow |
| `REDIS_HOST` | Redis 服务器主机名 | localhost |
| `REDIS_PORT` | Redis 服务器端口 | 6379 |
| `SECRET_KEY` | 用于 JWT 令牌的密钥 | random_secure_string |
| `LLM_API_BASE` | LLM API 基本 URL | https://api.openai.com/v1 |
| `LLM_API_KEY` | LLM API 密钥 | sk-... |
| `EMBEDDING_MODEL` | 嵌入模型名称 | text-embedding-ada-002 |
| `SENTRY_DSN` | Sentry 错误跟踪 DSN | https://... |
| `ENVIRONMENT` | 环境名称 (local, dev, prod) | local |

## 附录B：常用命令

```bash
# 启动开发服务器
uv run python main.py runserver

# 运行数据库迁移
alembic upgrade head

# 生成新的迁移
alembic revision --autogenerate -m "描述"

# 运行测试
pytest

# 运行特定模块的测试
pytest tests/test_api/test_chat.py

# 运行评估
uv run python main.py runeval --dataset regression
```

## 附录C：功能开发路线图

1. **多语言支持**：添加更多语言的支持
2. **高级检索功能**：实现更复杂的检索策略
3. **用户反馈系统**：收集和利用用户反馈改进回答
4. **多模态支持**：处理图像和视频内容
5. **自定义提示模板**：允许用户定义自己的提示模板
6. **A/B测试**：比较不同模型和策略的性能 