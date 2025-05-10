# AutoFlow (tidb-ai) 项目结构详解

## 项目概述

AutoFlow是一个基于图形RAG(GraphRAG)的对话式知识库工具，构建于TiDB向量存储、LlamaIndex和DSPy之上。该项目提供了类似Perplexity的对话式搜索页面和可嵌入的JavaScript小部件，方便用户将对话式搜索功能集成到自己的网站中。

## 顶层目录结构

```
tidb-ai/
├── autoflow-env/         # Python虚拟环境目录
├── frontend/             # 前端应用代码
├── e2e/                  # 端到端测试目录
├── docs/                 # 项目文档
├── core/                 # 核心业务逻辑模块
├── backend/              # 后端服务代码
├── docker-compose.yml    # 主Docker部署配置
├── docker-compose-cn.yml # 针对中国网络环境优化的Docker配置
├── docker-compose.dev.yml # 开发环境Docker配置
├── CONTRIBUTING.md       # 项目贡献指南
├── LICENSE.txt           # Apache 2.0许可证
└── README.md             # 项目概览和快速入门指南
```

## 详细目录和文件说明

### 1. 前端目录 (frontend/)

前端基于Next.js框架构建，使用TypeScript、Tailwind CSS和shadcn/ui设计系统。

```
frontend/
├── app/                  # 主要前端应用代码
│   ├── src/              # 源代码目录
│   │   ├── lib/          # 工具库和辅助函数
│   │   ├── experimental/ # 实验性功能
│   │   ├── hooks/        # React钩子函数
│   │   ├── components/   # UI组件
│   │   ├── core/         # 核心业务逻辑
│   │   ├── app/          # Next.js应用路由和页面
│   │   └── api/          # 前端API客户端
│   ├── public/           # 静态资源目录
│   ├── tailwind.config.ts # Tailwind CSS配置
│   ├── tsconfig.json     # TypeScript配置
│   ├── next.config.ts    # Next.js配置
│   ├── package.json      # 应用依赖和脚本
│   ├── postcss.config.mjs # PostCSS配置
│   ├── jest.config.ts    # Jest测试配置
│   ├── jest.polyfills.js # Jest测试polyfills
│   ├── .storybook/       # Storybook配置目录
│   ├── .eslintrc.json    # ESLint代码检查配置
│   ├── .gitignore        # Git忽略文件
│   ├── components.json   # UI组件配置
│   ├── next-sitemap.config.js # 网站地图配置
│   ├── notice.md         # 项目通知
│   └── README.md         # 前端应用说明
├── packages/             # 共享包和模块
├── patches/              # 依赖包补丁
├── pnpm-workspace.yaml   # pnpm工作区配置
├── pnpm-lock.yaml        # 依赖锁定文件
├── package.json          # 项目配置和脚本
├── Dockerfile            # 前端容器构建配置
├── .nvmrc                # Node.js版本配置
├── .prettierignore       # Prettier格式化忽略配置
└── .gitignore            # Git忽略文件配置
```

#### 前端组件目录详情 (frontend/app/src/components/)

组件目录包含所有UI组件，按功能模块分类组织：

```
components/
├── ui/                   # 基础UI组件库
├── system/               # 系统级组件
├── settings/             # 设置相关组件
├── settings-form/        # 设置表单组件
├── reranker/             # 重排模型组件
├── remark-content/       # Markdown内容渲染组件
├── llm/                  # LLM模型相关组件
├── nextjs/               # Next.js特定组件
├── icons/                # 图标组件
├── knowledge-base/       # 知识库相关组件
├── graph/                # 图形可视化组件
├── form/                 # 表单组件
├── evaluations/          # 评估相关组件
├── feedbacks/            # 反馈相关组件
├── documents/            # 文档处理组件
├── embedding-models/     # 嵌入模型组件
├── datasource/           # 数据源组件
├── chat/                 # 聊天界面组件
├── charts/               # 图表组件
├── chat-engine/          # 聊天引擎组件
├── auto-scroll/          # 自动滚动组件
├── cells/                # 单元格组件
├── api-keys/             # API密钥组件
└── auth/                 # 认证相关组件
```

#### 聊天组件详情 (frontend/app/src/components/chat/)

聊天组件是用户交互的核心部分，包含多个子组件：

```
chat/
├── ask.tsx                         # 提问组件
├── chat-controller.test.ts         # 聊天控制器测试
├── chat-controller.ts              # 聊天控制器逻辑
├── chat-hooks.tsx                  # 聊天相关钩子函数
├── chat-message-controller.test.ts # 消息控制器测试
├── chat-message-controller.ts      # 消息控制器逻辑
├── chat-new-dialog.tsx             # 新建聊天对话框
├── chat-stream-state.ts            # 聊天流状态管理
├── chat-stream.state.test.ts       # 聊天流状态测试
├── chats-history.tsx               # 聊天历史组件
├── chats-table.tsx                 # 聊天列表表格
├── conversation-message-groups.scss # 消息组样式
├── conversation-message-groups.tsx # 消息组组件
├── conversation.test.tsx           # 对话组件测试
├── conversation.tsx                # 对话组件
├── debug-info.tsx                  # 调试信息组件
├── knowledge-graph-debug-info.tsx  # 知识图谱调试组件
├── message-annotation-history-stackvm.tsx # 消息注释历史组件
├── message-annotation-history.tsx  # 消息注释历史组件
├── message-answer.tsx              # 消息回答组件
├── message-auto-scroll.tsx         # 消息自动滚动组件
├── message-beta-alert.tsx          # 测试版提示组件
├── message-content-sources.tsx     # 消息内容来源组件
├── message-content.test.tsx        # 消息内容测试
├── message-content.tsx             # 消息内容组件
├── message-error.tsx               # 消息错误组件
├── message-feedback.tsx            # 消息反馈组件
├── message-input.tsx               # 消息输入组件
├── message-operations.tsx          # 消息操作组件
├── message-recommend-questions.tsx # 推荐问题组件
├── message-section.tsx             # 消息部分组件
├── testutils.ts                    # 测试工具函数
├── use-ask.ts                      # 提问钩子函数
├── use-message-feedback.ts         # 消息反馈钩子函数
└── utils.ts                        # 工具函数
```

### 2. 后端目录 (backend/)

后端使用FastAPI框架构建，处理API请求、数据库交互和RAG逻辑。

```
backend/
├── app/                  # 主要后端应用代码
│   ├── alembic/          # 数据库迁移目录
│   ├── api/              # API路由和接口
│   │   ├── routes/       # 公共API路由
│   │   ├── admin_routes/ # 管理员API路由
│   │   ├── deps.py       # 依赖注入
│   │   ├── main.py       # API路由注册
│   │   └── __init__.py   # 包初始化
│   ├── auth/             # 认证和授权
│   ├── core/             # 核心功能
│   ├── evaluation/       # 评估系统
│   ├── experiments/      # 实验功能
│   ├── file_storage/     # 文件存储
│   ├── models/           # 数据模型
│   ├── rag/              # RAG实现
│   ├── repositories/     # 数据仓库
│   ├── site_settings/    # 站点设置
│   ├── staff_action/     # 管理员操作
│   ├── tasks/            # 后台任务
│   ├── utils/            # 工具函数
│   ├── api_server.py     # API服务器配置
│   ├── celery.py         # Celery任务队列配置
│   ├── exceptions.py     # 异常定义
│   ├── logger.py         # 日志配置
│   ├── types.py          # 类型定义
│   └── __init__.py       # 包初始化
├── tests/                # 测试目录
├── local_embedding_reranker/ # 本地嵌入和重排模型
├── dspy_compiled_program/ # DSPy编译程序
├── main.py               # 后端入口文件
├── bootstrap.py          # 系统初始化脚本
├── dspy_program.py       # DSPy程序定义
├── pyproject.toml        # Python项目配置
├── supervisord.conf      # Supervisor进程管理配置
├── alembic.ini           # Alembic数据库迁移配置
├── prestart.sh           # 容器启动前脚本
├── Dockerfile            # 后端容器构建配置
├── Makefile              # 项目构建和管理脚本
├── README.md             # 后端说明文档
├── .python-version       # Python版本配置
├── .pre-commit-config.yaml # Git钩子配置
├── .dockerignore         # Docker构建忽略配置
├── .gitignore            # Git忽略文件配置
└── uv.lock               # Python依赖锁定文件
```

### 3. 核心模块目录 (core/)

核心模块包含AutoFlow的关键业务逻辑和数据处理功能。

```
core/
├── autoflow/             # 核心功能模块
│   ├── chunkers/         # 文档分块工具
│   ├── configs/          # 配置管理
│   ├── knowledge_base/   # 知识库功能
│   ├── knowledge_graph/  # 知识图谱功能
│   ├── loaders/          # 数据加载器
│   ├── models/           # 数据模型
│   ├── orms/             # ORM映射
│   ├── storage/          # 存储接口
│   ├── utils/            # 工具函数
│   ├── __init__.py       # 包初始化
│   ├── data_types.py     # 数据类型定义
│   ├── db.py             # 数据库连接
│   ├── main.py           # 核心模块入口
│   ├── py.typed          # 类型标记文件
│   └── types.py          # 类型定义
├── examples/             # 示例代码
├── experimental/         # 实验性功能
├── tests/                # 测试代码
├── .cursor/              # Cursor编辑器配置
├── .gitignore            # Git忽略文件配置
├── .python-version       # Python版本配置
├── Makefile              # 构建和管理脚本
├── README.md             # 核心模块说明
├── pyproject.toml        # Python项目配置
└── uv.lock               # 依赖锁定文件
```

### 4. 文档目录 (docs/)

包含项目文档，使用Nextra构建。

```
docs/
├── src/                  # 源代码目录
│   ├── app/              # Nextra应用
│   └── content/          # 文档内容
│       ├── releases/     # 版本发布说明
│       ├── _meta.ts      # 文档元数据
│       ├── chat-engine.mdx # 聊天引擎文档
│       ├── deploy-with-docker.mdx # Docker部署指南
│       ├── embedding-model.mdx # 嵌入模型文档
│       ├── evaluation.mdx # 评估系统文档
│       ├── faq.mdx       # 常见问题解答
│       ├── index.mdx     # 文档主页
│       ├── javascript.mdx # JavaScript小部件文档
│       ├── knowledge-base.mdx # 知识库文档
│       ├── llm.mdx       # LLM模型文档
│       ├── quick-start.mdx # 快速入门指南
│       ├── README.md     # 文档说明
│       ├── requirements.mdx # 系统要求
│       ├── reranker-model.mdx # 重排模型文档
│       └── resources.mdx # 资源链接
├── public/               # 静态资源
├── .gitignore            # Git忽略文件配置
├── mdx-components.ts     # MDX组件配置
├── next-env.d.ts         # Next.js类型声明
├── next-sitemap.config.js # 网站地图配置
├── next.config.mjs       # Next.js配置
├── package.json          # 项目依赖和脚本
├── pnpm-lock.yaml        # 依赖锁定文件
└── tsconfig.json         # TypeScript配置
```

### 5. 端到端测试目录 (e2e/)

包含端到端测试代码，验证系统功能的完整性。

```
e2e/
├── tests/                # 测试用例
├── playwright.config.ts  # Playwright配置
└── package.json          # 测试依赖和脚本
```

### 6. Docker配置文件

#### docker-compose.yml

主要Docker部署配置文件，定义了以下服务：
- redis: 缓存和任务队列服务
- backend: 后端API服务
- frontend: 前端Web界面
- background: 后台任务处理服务
- local-embedding-reranker: 本地嵌入和重排模型服务（可选）

#### docker-compose-cn.yml

针对中国网络环境优化的Docker配置，使用国内镜像源，包含与主配置相同的服务，但增加了以下配置：
- 使用阿里云镜像源
- 为Hugging Face模型配置了国内镜像

#### docker-compose.dev.yml

开发环境配置，提供更便捷的开发体验，特点包括：
- 挂载本地代码目录，支持实时代码更新
- 暴露更多调试端口
- 配置开发环境变量

## 核心技术栈

- **前端**: Next.js, TypeScript, Tailwind CSS, shadcn/ui
- **后端**: FastAPI, Celery, SQLAlchemy, Alembic
- **数据库**: TiDB（向量存储）
- **AI/ML**: LlamaIndex, DSPy, 各种嵌入和重排模型
- **缓存**: Redis
- **容器化**: Docker, Docker Compose
- **测试**: Jest, Playwright
- **文档**: Nextra, MDX

## 功能模块说明

1. **对话式搜索**: 提供类似Perplexity的交互体验，支持上下文相关的问答
2. **知识库管理**: 包含文档导入、处理和管理功能
3. **知识图谱**: 构建和利用图形化的知识表示
4. **嵌入模型**: 支持多种文本嵌入模型，提供向量化能力
5. **重排模型**: 优化检索结果的相关性排序
6. **JS小部件**: 可嵌入到第三方网站的对话窗口
7. **管理后台**: 提供系统配置、用户管理和数据分析功能
8. **评估系统**: 测试和评估RAG系统性能 