# AutoFlow 工作流系统改造

本项目旨在改造现有的工作流系统，实现更灵活、可扩展的架构，以支持各种AI工具的无缝集成和高效的事件处理。

## 项目背景

原有的工作流系统存在以下问题：
1. 事件系统与工具系统分离，导致工具调用与事件处理不统一
2. 缺乏规范化的工具接口，使得新工具的集成困难
3. 事件流的处理效率不高，事件转换复杂

本次改造旨在解决以上问题，实现一个统一的工具框架和事件系统。

## 改造阶段

### 第一阶段：基础框架搭建 - 工具与事件系统

- 创建 `events/tool_events.py`：定义工具相关的事件类型
- 创建 `events/converter.py`：实现事件转换器，处理内部事件与前端事件的转换
- 规范化 `tools/base.py`：定义工具的基类和接口规范
- 规范化 `tools/registry.py`：实现工具注册表，管理工具的注册和获取
- 编写单元测试：验证工具框架的基础功能

### 第二阶段：核心工具实现与注册

- 实现/规范化 `KnowledgeGraphTool`：知识图谱查询工具
- 实现/规范化 `KnowledgeRetrievalTool`：知识检索工具
- 实现/规范化 `DatabaseQueryTool`：数据库查询工具
- 实现/规范化 `FurtherQuestionsTool`：后续问题生成工具
- 实现工具初始化脚本 `tools/init.py`：统一注册和初始化所有工具
- 扩展单元测试：验证各工具的功能和集成

### 第三阶段：智能体与工作流引擎集成

- 实现 `BaseAgent` 与工具框架的集成
  - 添加工具调用方法 `call_tool`
  - 实现事件发送器 `emit_event`
  - 规范化事件处理流程
- 实现工作流引擎与Agent的集成
  - 工作流引擎处理事件流的逻辑
  - 事件传递和状态管理
- 创建集成测试
  - 验证Agent工具调用：`verify_agent_integration.py`
  - 验证工作流完整集成：`verify_integration.py`

### 第四阶段：优化与扩展（计划中）

- 性能优化：减少事件转换开销，优化事件流处理
- 工具扩展：添加更多AI工具，如LLM调用、多模态处理等
- 监控与可视化：添加工作流监控和可视化功能
- 前端集成：实现前端与工作流系统的深度集成

## 验证与测试

### 工具框架验证

运行以下命令验证工具框架是否正确实现：

```bash
python -m app.autoflow.verify_tools_fix
```

### Agent集成验证

运行以下命令验证Agent是否成功集成工具框架：

```bash
python -m app.autoflow.verify_agent_integration
```

### 工作流完整集成验证

运行以下命令验证工作流、Agent与工具框架的完整集成：

```bash
python -m app.autoflow.verify_integration
```

## 目录结构

```
app/
  autoflow/
    __init__.py             # 模块初始化
    workflow.py             # 工作流实现
    context.py              # 上下文管理
    events/
      __init__.py           # 事件模块初始化
      tool_events.py        # 工具事件定义
      converter.py          # 事件转换器
    tools/
      __init__.py           # 工具模块初始化
      base.py               # 工具基类和接口
      registry.py           # 工具注册表
      knowledge_graph_tool.py  # 知识图谱工具
      knowledge_retrieval_tool.py # 知识检索工具
      database_query_tool.py  # 数据库查询工具
      further_questions_tool.py  # 后续问题工具
      init.py               # 工具初始化脚本
    agents/
      __init__.py           # 代理模块初始化
      base_agent.py         # 基础代理类
    verify_tools_fix.py     # 工具框架验证
    verify_agent_integration.py  # Agent集成验证
    verify_integration.py   # 完整工作流验证
```

## 使用指南

1. 导入并初始化工具注册表：
   ```python
   from app.autoflow.tools.init import register_tools
   
   tool_registry = register_tools(db_session=session, engine_config=config)
   ```

2. 创建Agent并绑定工具：
   ```python
   from app.autoflow.agents.base_agent import BaseAgent
   
   class MyAgent(BaseAgent):
       # 实现自定义Agent逻辑
       
   agent = MyAgent(tool_registry=tool_registry)
   ```

3. 创建工作流并处理事件：
   ```python
   from app.autoflow.workflow import Workflow
   from app.autoflow.context import Context
   from app.autoflow.events import StartEvent
   
   workflow = Workflow(agent=agent)
   ctx = Context()
   event = StartEvent()
   
   # 处理事件
   result = await workflow.process(ctx, event)
   ``` 