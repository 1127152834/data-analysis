# AutoFlow (tidb-ai) 二次开发指南

本文档提供了基于AutoFlow项目进行二次开发的指南和最佳实践，帮助开发者理解系统架构并进行功能扩展或定制。

## 一、系统架构概述

AutoFlow使用典型的前后端分离架构，主要由以下几个部分组成：

### 1.1 系统组件

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│    前端     │ <--> │    后端     │ <--> │   TiDB数据库 │
│  (Next.js)  │      │  (FastAPI)  │      │  (向量存储)  │
└─────────────┘      └─────────────┘      └─────────────┘
                           ^
                           │
                           v
                     ┌─────────────┐
                     │   核心模块   │
                     │ (AutoFlow)  │
                     └─────────────┘
                           ^
                           │
                           v
                     ┌─────────────┐
                     │   外部服务   │
                     │ (LLM API等) │
                     └─────────────┘
```

### 1.2 代码架构

- **前端**：使用Next.js框架，基于React和TypeScript开发
- **后端**：使用FastAPI框架，处理API请求和业务逻辑
- **核心模块**：实现知识库、检索、向量存储等核心功能
- **任务处理**：使用Celery处理异步任务，如文档处理和网站爬取

## 二、开发环境搭建

在进行二次开发前，需要搭建适合的开发环境。

### 2.1 前端开发环境

```bash
# 进入前端目录
cd frontend/app

# 安装依赖
pnpm install

# 启动开发服务器
pnpm dev
```

前端开发服务器会在 http://localhost:3000 运行，支持热更新。

### 2.2 后端开发环境

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python -m venv venv
# 或使用uv (推荐)
uv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e ".[dev]"
# 或使用uv (推荐)
uv pip install -e ".[dev]"

# 启动后端服务
uvicorn app.api_server:app --reload --host 0.0.0.0 --port 8000
```

注意：后端服务需要有可用的TiDB数据库和Redis服务。

### 2.3 使用Docker开发环境

更简便的方法是使用项目提供的开发环境Docker配置：

```bash
# 启动开发环境
docker compose -f docker-compose.dev.yml up -d

# 查看日志
docker compose -f docker-compose.dev.yml logs -f
```

这种方式会将本地代码目录挂载到容器中，便于开发和调试。

## 三、前端开发指南

### 3.1 项目结构

前端项目采用模块化结构，位于 `frontend/app` 目录下：

```
frontend/app/
├── src/                # 源代码
│   ├── app/            # 页面和路由
│   ├── components/     # 组件
│   ├── lib/            # 工具库
│   ├── hooks/          # React钩子
│   ├── api/            # API请求
│   └── core/           # 核心逻辑
├── public/             # 静态资源
├── tailwind.config.ts  # Tailwind配置
└── package.json        # 项目配置
```

### 3.2 新增/修改页面

1. 在 `src/app` 目录下创建新的路由文件夹和页面

```tsx
// src/app/(main)/custom-page/page.tsx
"use client";

import { PageLayout } from "@/components/ui/page-layout";

export default function CustomPage() {
  return (
    <PageLayout>
      <h1>自定义页面</h1>
      <p>这是一个自定义页面示例</p>
    </PageLayout>
  );
}
```

2. 添加导航链接（可选）

```tsx
// src/components/site-nav.tsx 中添加导航项
{
  name: "自定义页面",
  href: "/custom-page",
  icon: CustomIcon,
}
```

### 3.3 创建新组件

在 `src/components` 目录下创建新组件：

```tsx
// src/components/custom/my-component.tsx
import { Button } from "@/components/ui/button";

interface MyComponentProps {
  title: string;
  onAction: () => void;
}

export function MyComponent({ title, onAction }: MyComponentProps) {
  return (
    <div className="p-4 border rounded-md">
      <h3 className="text-lg font-medium">{title}</h3>
      <Button onClick={onAction}>执行操作</Button>
    </div>
  );
}
```

### 3.4 API调用

使用前端API客户端进行后端API调用：

```tsx
import { api } from "@/api";

// 获取数据
const fetchData = async () => {
  try {
    const response = await api.get("/custom-endpoint");
    return response.data;
  } catch (error) {
    console.error("获取数据失败", error);
    return null;
  }
};

// 提交数据
const submitData = async (data: any) => {
  try {
    const response = await api.post("/custom-endpoint", data);
    return response.data;
  } catch (error) {
    console.error("提交数据失败", error);
    return null;
  }
};
```

### 3.5 状态管理

使用React钩子进行状态管理：

```tsx
import { useState, useEffect } from "react";
import { api } from "@/api";

export function useCustomData(id: string) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/custom-endpoint/${id}`);
        setData(response.data);
        setError(null);
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  return { data, loading, error };
}
```

## 四、后端开发指南

### 4.1 项目结构

后端项目采用模块化结构，位于 `backend/app` 目录下：

```
backend/app/
├── api/                # API路由
│   ├── routes/         # 公共API路由
│   └── admin_routes/   # 管理员API路由
├── models/             # 数据模型
├── repositories/       # 数据仓库
├── rag/                # RAG实现
├── utils/              # 工具函数
├── tasks/              # 异步任务
└── api_server.py       # 应用入口
```

### 4.2 添加新API端点

1. 在 `app/api/routes` 目录下创建新的路由文件

```python
# app/api/routes/custom.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from app.auth.users import current_active_user
from app.models.user import User
from app.models.custom import CustomModel
from app.repositories.custom import CustomRepository

router = APIRouter(prefix="/custom", tags=["custom"])

@router.get("/")
async def list_items(
    current_user: User = Depends(current_active_user),
) -> List[CustomModel]:
    """获取自定义项目列表"""
    repository = CustomRepository()
    items = await repository.list_items(user_id=current_user.id)
    return items

@router.post("/")
async def create_item(
    item: CustomModel,
    current_user: User = Depends(current_active_user),
) -> CustomModel:
    """创建新的自定义项目"""
    repository = CustomRepository()
    created_item = await repository.create_item(item, user_id=current_user.id)
    return created_item
```

2. 在 `app/api/main.py` 中注册路由

```python
# 在文件顶部添加导入
from app.api.routes import custom

# 在 api_router 定义部分添加
api_router.include_router(custom.router, tags=["custom"])
```

### 4.3 创建数据模型

在 `app/models` 目录下创建新的数据模型：

```python
# app/models/custom.py
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

class CustomModel(BaseModel):
    """自定义数据模型"""
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Optional[UUID] = None

    class Config:
        orm_mode = True
```

### 4.4 实现数据仓库

在 `app/repositories` 目录下创建新的数据仓库：

```python
# app/repositories/custom.py
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select
from app.models.custom import CustomModel
from app.core.database import get_session

class CustomRepository:
    """自定义数据仓库"""
    
    async def list_items(self, user_id: UUID) -> List[CustomModel]:
        """获取用户的自定义项目列表"""
        async with get_session() as session:
            query = select(CustomModel).where(CustomModel.user_id == user_id)
            result = await session.execute(query)
            return result.scalars().all()
    
    async def create_item(self, item: CustomModel, user_id: UUID) -> CustomModel:
        """创建新的自定义项目"""
        item.user_id = user_id
        async with get_session() as session:
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return item
```

### 4.5 添加异步任务

在 `app/tasks` 目录下创建新的异步任务：

```python
# app/tasks/custom_task.py
from celery import shared_task
from app.logger import get_logger

logger = get_logger(__name__)

@shared_task(bind=True)
def process_custom_data(self, data_id: str):
    """处理自定义数据的任务"""
    logger.info(f"开始处理数据: {data_id}")
    
    try:
        # 实现你的数据处理逻辑
        logger.info(f"数据处理完成: {data_id}")
        return {"status": "success", "data_id": data_id}
    except Exception as e:
        logger.error(f"数据处理失败: {data_id}, 错误: {str(e)}")
        raise
```

## 五、核心模块开发指南

### 5.1 项目结构

核心模块采用模块化结构，位于 `core/autoflow` 目录下：

```
core/autoflow/
├── knowledge_base/     # 知识库功能
├── knowledge_graph/    # 知识图谱功能
├── chunkers/           # 文档分块
├── loaders/            # 数据加载器
├── models/             # 数据模型
├── storage/            # 存储接口
└── utils/              # 工具函数
```

### 5.2 扩展知识库功能

在 `autoflow/knowledge_base` 目录下扩展功能：

```python
# autoflow/knowledge_base/custom_processor.py
from typing import List, Dict, Any
from autoflow.knowledge_base.base import BaseProcessor
from autoflow.models.document import Document

class CustomProcessor(BaseProcessor):
    """自定义文档处理器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 初始化自定义配置
        self.custom_option = config.get("custom_option", "default_value")
    
    async def process(self, document: Document) -> Document:
        """处理文档"""
        # 实现自定义文档处理逻辑
        document.metadata["processed_by"] = "custom_processor"
        document.metadata["custom_option"] = self.custom_option
        
        # 处理文档内容
        # ...
        
        return document
```

### 5.3 创建自定义分块器

在 `autoflow/chunkers` 目录下创建自定义分块器：

```python
# autoflow/chunkers/custom_chunker.py
from typing import List, Dict, Any
from autoflow.chunkers.base import BaseChunker
from autoflow.models.document import Document, DocumentChunk

class CustomChunker(BaseChunker):
    """自定义文档分块器"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.chunk_size = config.get("chunk_size", 1000)
        self.chunk_overlap = config.get("chunk_overlap", 200)
    
    def chunk(self, document: Document) -> List[DocumentChunk]:
        """将文档分割成块"""
        chunks = []
        text = document.text
        
        # 实现自定义分块逻辑
        # 例如: 按段落、句子或自定义规则分块
        # ...
        
        # 创建文档块
        for i, chunk_text in enumerate(text_chunks):
            chunk = DocumentChunk(
                text=chunk_text,
                metadata={
                    **document.metadata,
                    "chunk_index": i,
                    "document_id": document.id,
                }
            )
            chunks.append(chunk)
        
        return chunks
```

## 六、数据库扩展指南

### 6.1 添加新的数据库表

使用Alembic创建新的数据库迁移：

```bash
# 进入后端目录
cd backend

# 创建新的迁移
alembic revision --autogenerate -m "Add custom table"
```

编辑生成的迁移文件，定义新表结构：

```python
# app/alembic/versions/xxxx_add_custom_table.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

def upgrade():
    op.create_table(
        'custom_items',
        sa.Column('id', UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', UUID(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('custom_items')
```

应用迁移：

```bash
alembic upgrade head
```

### 6.2 使用向量存储

在TiDB中使用向量存储功能：

```python
from autoflow.storage.tidb_vector import TiDBVectorStorage

# 创建向量存储实例
vector_storage = TiDBVectorStorage(
    connection_string="mysql+pymysql://user:password@host:port/database",
    table_name="custom_vectors",
    dimension=1536  # 向量维度
)

# 存储向量
await vector_storage.store(
    vectors=[
        {
            "id": "doc1",
            "vector": [0.1, 0.2, ...],  # 1536维向量
            "metadata": {"source": "custom", "type": "document"}
        }
    ]
)

# 查询相似向量
results = await vector_storage.search(
    query_vector=[0.1, 0.2, ...],
    k=5,  # 返回前5个最相似的结果
    filter={"metadata.type": "document"}
)
```

## 七、扩展聊天功能

### 7.1 自定义提示模板

创建自定义聊天提示模板：

```python
# app/rag/prompts/custom_prompt.py
from string import Template
from typing import Dict, Any

class CustomPromptTemplate:
    """自定义提示模板"""
    
    def __init__(self):
        self.system_template = Template("""
你是一个专业的助手，基于以下知识库信息回答用户问题。
知识库信息:
$context

如果无法从知识库中找到答案，请清晰地表明你不知道，不要编造信息。
""")
        
        self.user_template = Template("问题: $question")
    
    def format(self, **kwargs) -> Dict[str, str]:
        """格式化提示模板"""
        context = kwargs.get("context", "")
        question = kwargs.get("question", "")
        
        return {
            "system": self.system_template.substitute(context=context),
            "user": self.user_template.substitute(question=question),
        }
```

### 7.2 自定义聊天引擎

创建自定义聊天引擎：

```python
# app/rag/engines/custom_engine.py
from typing import Dict, Any, List
from app.rag.engines.base import BaseEngine
from app.rag.prompts.custom_prompt import CustomPromptTemplate
from app.rag.retrievers import get_retriever
from app.logger import get_logger

logger = get_logger(__name__)

class CustomChatEngine(BaseEngine):
    """自定义聊天引擎"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.prompt_template = CustomPromptTemplate()
        self.retriever = get_retriever(config.get("retriever", {}))
        self.max_tokens = config.get("max_tokens", 2000)
    
    async def generate(self, query: str, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """生成回答"""
        try:
            # 检索相关文档
            docs = await self.retriever.retrieve(query)
            
            # 准备上下文
            context = "\n\n".join([doc.text for doc in docs])
            
            # 格式化提示
            messages = self.prompt_template.format(
                context=context,
                question=query
            )
            
            # 构建完整的消息列表
            full_messages = [
                {"role": "system", "content": messages["system"]},
                {"role": "user", "content": messages["user"]}
            ]
            
            # 调用LLM生成回答
            response = await self.llm.generate(
                messages=full_messages,
                max_tokens=self.max_tokens
            )
            
            return {
                "answer": response["content"],
                "sources": [{"id": doc.id, "text": doc.text} for doc in docs]
            }
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            return {
                "answer": "抱歉，处理您的请求时出现错误。",
                "sources": []
            }
```

## 八、自定义LLM集成

### 8.1 添加新的LLM提供商

在 `app/models/llm.py` 中添加新的LLM提供商：

```python
# 在LLMProvider枚举中添加
class LLMProvider(str, Enum):
    # 现有提供商
    OPENAI = "openai"
    AZURE = "azure"
    # 新增提供商
    CUSTOM = "custom"
```

创建自定义LLM实现：

```python
# app/rag/llm/custom_llm.py
from typing import Dict, Any, List
from app.rag.llm.base import BaseLLM

class CustomLLM(BaseLLM):
    """自定义LLM实现"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config["api_key"]
        self.api_base = config.get("api_base", "https://api.custom-llm.com")
        self.model = config.get("model", "default-model")
    
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """生成回答"""
        try:
            # 实现与自定义LLM API的集成
            # ...
            
            # 返回响应
            return {
                "content": response_text,
                "model": self.model,
                "provider": "custom",
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                }
            }
        except Exception as e:
            raise Exception(f"CustomLLM 生成失败: {str(e)}")
```

### 8.2 添加到LLM工厂

在 `app/rag/llm/factory.py` 中添加自定义LLM：

```python
from app.rag.llm.custom_llm import CustomLLM

def get_llm(config: Dict[str, Any]) -> BaseLLM:
    """获取LLM实例"""
    provider = config.get("provider", "openai")
    
    if provider == "openai":
        return OpenAILLM(config)
    elif provider == "azure":
        return AzureLLM(config)
    elif provider == "custom":  # 添加自定义LLM
        return CustomLLM(config)
    else:
        raise ValueError(f"不支持的LLM提供商: {provider}")
```

## 九、汉化与本地化

### 9.1 前端汉化

前端文本汉化可以通过以下方式实现：

1. 创建语言文件

```typescript
// src/lib/i18n/zh-CN.ts
export const translations = {
  common: {
    search: "搜索",
    cancel: "取消",
    confirm: "确认",
    delete: "删除",
    edit: "编辑",
    save: "保存",
    create: "创建",
    close: "关闭",
  },
  nav: {
    home: "首页",
    chat: "聊天",
    knowledgeBase: "知识库",
    settings: "设置",
    admin: "管理",
  },
  // 更多翻译...
};
```

2. 创建国际化钩子

```typescript
// src/hooks/use-translation.ts
import { translations } from "@/lib/i18n/zh-CN";

export function useTranslation() {
  // 这里可以扩展为支持多语言
  return {
    t: (key: string) => {
      const keys = key.split(".");
      let result = translations;
      for (const k of keys) {
        if (result[k] === undefined) {
          return key; // 返回key作为后备
        }
        result = result[k];
      }
      return result;
    }
  };
}
```

3. 在组件中使用

```tsx
import { useTranslation } from "@/hooks/use-translation";

export function MyComponent() {
  const { t } = useTranslation();
  
  return (
    <div>
      <h1>{t("nav.home")}</h1>
      <button>{t("common.save")}</button>
    </div>
  );
}
```

### 9.2 后端汉化

后端可以通过修改错误消息和日志消息来实现汉化：

```python
# app/exceptions.py
class CustomException(Exception):
    """自定义异常基类"""
    def __init__(self, message="发生错误"):
        self.message = message
        super().__init__(self.message)

class ResourceNotFoundException(CustomException):
    """资源未找到异常"""
    def __init__(self, resource_type="资源", resource_id=None):
        message = f"未找到{resource_type}"
        if resource_id:
            message += f"(ID: {resource_id})"
        super().__init__(message)
```

### 9.3 文档汉化

将文档内容翻译为中文，存放在 `docs/src/content/zh` 目录下：

```markdown
# 快速入门

本文档将指导您如何快速开始使用AutoFlow系统。

## 前提条件

在开始使用前，请确保您已完成以下准备工作：

- 已部署AutoFlow系统
- 已创建管理员账户
- 已配置TiDB数据库连接

## 登录系统

访问系统首页，点击右上角的"登录"按钮...
```

## 十、部署与发布

### 10.1 构建前端资源

构建生产环境前端资源：

```bash
cd frontend/app
pnpm build
```

### 10.2 构建Docker镜像

构建自定义Docker镜像：

```bash
# 构建前端镜像
docker build -t your-registry/autoflow-frontend:custom ./frontend

# 构建后端镜像
docker build -t your-registry/autoflow-backend:custom ./backend
```

### 10.3 发布镜像

将镜像发布到Docker仓库：

```bash
docker push your-registry/autoflow-frontend:custom
docker push your-registry/autoflow-backend:custom
```

### 10.4 更新部署配置

修改docker-compose.yml使用自定义镜像：

```yaml
services:
  backend:
    image: your-registry/autoflow-backend:custom
    # ...
  
  frontend:
    image: your-registry/autoflow-frontend:custom
    # ...
```

## 十一、常见开发问题

### 11.1 TypeScript类型错误

**问题**: 前端开发时遇到TypeScript类型错误

**解决方案**:
1. 检查类型定义是否正确
2. 使用正确的类型声明
3. 适当使用类型断言或泛型

### 11.2 API通信问题

**问题**: 前端无法与后端API通信

**解决方案**:
1. 检查API路径是否正确
2. 验证CORS配置
3. 检查身份验证状态
4. 查看网络请求日志

### 11.3 数据库迁移问题

**问题**: Alembic数据库迁移失败

**解决方案**:
1. 检查迁移文件
2. 验证数据库连接
3. 尝试手动执行SQL语句
4. 必要时回滚迁移

### 11.4 部署问题

**问题**: Docker部署失败

**解决方案**:
1. 检查Docker日志
2. 验证环境变量配置
3. 确认网络设置
4. 检查磁盘空间 