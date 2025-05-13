# 数据库智能查询集成开发计划

本文档详细描述了在AutoFlow项目中集成LlamaIndex的function calling功能，使大模型能够根据对话上下文自主调用数据库查询工具的开发计划。

## 项目概述

**目标**：增强AutoFlow聊天功能，使大模型能够自动识别需要查询数据库的场景，选择合适的数据库连接，构建查询语句，执行查询并将结果整合至对话响应中。

**核心功能**：
1. 根据数据库连接元数据动态创建数据库查询工具
2. 使大模型能够在对话中自主决定何时调用数据库查询
3. 记录并展示查询执行过程与结果
4. 将数据库元数据集成至知识图谱，进一步增强数据理解

## 新增功能：工具调用模式选项

为了满足不同场景的需求，系统现在支持两种工具调用模式，可通过配置选择：

### 1. 引导模式 (guided)

- **默认模式**
- 系统先通过关键词匹配和相关性评估来判断是否需要使用数据库工具
- 只有在判断需要查询数据库时才会调用代理和相关工具
- **优势**：更加高效，减少不必要的调用，响应更快
- **适用场景**：大部分问题偏知识类，数据查询较少的场景

### 2. 自主模式 (autonomous)

- **新增模式**
- 直接将所有工具提供给大模型，让它完全自主决定是否使用
- 绕过系统的预判断逻辑，充分发挥大模型的判断能力
- **优势**：处理复杂场景和混合查询更智能，减少漏判情况
- **适用场景**：数据分析场景，用户问题复杂且经常需要查询数据库

### 配置方法

可以通过以下方式配置工具调用模式：

```python
# 在代码中配置
config = ChatEngineConfig()
config.database.tool_mode = "autonomous"  # 或 "guided"(默认)

# 在API中配置
{
  "database": {
    "enabled": true,
    "tool_mode": "autonomous"
  }
}
```

### 性能考虑

- 自主模式下，系统会在每次查询中将所有数据库工具提供给模型
- 当数据库连接较多时，可能会增加模型的推理负担和响应时间
- 建议在数据库连接较少（10个以内）的场景中使用自主模式

## 开发路线图

### 阶段一：核心功能开发

1. 基础架构和数据模型增强
   1. ✅ 增强ChatEngineConfig关联数据库连接
      - 在ChatEngineConfig中添加active_database_connections属性
      - 修改load_from_db方法加载数据库连接
   2. ✅ 创建数据库工具工厂模块
      - 创建app/rag/tools/database_tools.py
      - 实现创建LlamaIndex SQLDatabase对象
      - 实现数据库查询工具创建
      - 处理数据库连接测试
   3. ✅ 集成工具调用到ChatFlow
      - 修改ChatFlow支持工具调用能力
      - 在初始化时创建数据库工具
      - 实现判断是否应使用数据库工具的逻辑
      - 使用ReActAgent进行工具调用

### 阶段二：集成到Chat Flow（预计工时：4-5天）

#### 任务2.1：修改ChatFlow初始化以支持数据库工具
- **文件位置**：`backend/app/rag/chat/chat_flow.py`
- **实现逻辑**：
  ```python
  # 添加所需导入
  from app.rag.tools.database_tools import create_database_connection_tools
  from llama_index.agent.openai import OpenAIAgent
  
  # 在ChatFlow.__init__方法中添加
  def __init__(self, ...现有参数...):
      # ...现有代码...
      
      # 初始化数据库查询工具
      self.database_query_tools = []
      if hasattr(self.engine_config, "active_database_connections"):
          if self.engine_config.active_database_connections:
              self.database_query_tools = create_database_connection_tools(
                  self.engine_config.active_database_connections,
                  self._llm  # 使用主LLM，因为需要理解复杂的数据库schema
              )
              logger.info(f"已创建 {len(self.database_query_tools)} 个数据库查询工具")
      
      # 初始化代理（如果有工具可用）
      # 注意：这里如果要支持其他工具，可以扩展all_tools
      all_tools = self.database_query_tools
      if all_tools:
          self.agent = OpenAIAgent.from_tools(
              tools=all_tools,
              llm=self._llm,
              verbose=True,  # 便于调试
              system_prompt="""你是一个智能助手，可以通过提供的工具查询数据库。
              根据用户问题，判断是否需要查询数据库来回答。
              如果需要查询数据库，请以自然语言格式构建清晰的查询。
              基于查询结果提供准确的回答，并在合适时引用数据来源。
              如果涉及多个数据库工具，选择最合适的或者依次使用多个工具。
              """
          )
      else:
          self.agent = None
  ```
- **验证方法**：
  - 单元测试：验证不同的ChatEngineConfig配置下ChatFlow能正确初始化工具和代理
  - 集成测试：在包含测试数据库的测试环境中初始化ChatFlow并检查工具列表

#### 任务2.2：修改ChatFlow._builtin_chat支持代理决策
- **文件位置**：`backend/app/rag/chat/chat_flow.py`
- **实现逻辑**：
  ```python
  def _builtin_chat(self):
      # 保存当前的追踪上下文
      ctx = langfuse_instrumentor_context.get().copy()
      
      # 步骤1: 创建聊天消息记录
      db_user_message, db_assistant_message = yield from self._chat_start()
      
      # 恢复追踪上下文
      langfuse_instrumentor_context.get().update(ctx)
      
      # 步骤2: (可选) 搜索知识图谱获取上下文
      knowledge_graph, knowledge_graph_context = yield from self._search_knowledge_graph(user_question=self.user_question)
      
      # 步骤3: 重写用户问题以增强检索效果
      refined_question = yield from self._refine_user_question(
          user_question=self.user_question,
          chat_history=self.chat_history,
          knowledge_graph_context=knowledge_graph_context,
          refined_question_prompt=self.engine_config.llm.condense_question_prompt,
      )
      
      # 步骤4: 检查问题是否需要澄清
      if self.engine_config.clarify_question:
          need_clarify, need_clarify_response = yield from self._clarify_question(
              user_question=refined_question,
              chat_history=self.chat_history,
              knowledge_graph_context=knowledge_graph_context,
          )
          if need_clarify:
              yield from self._chat_finish(
                  db_assistant_message=db_assistant_message,
                  db_user_message=db_user_message,
                  response_text=need_clarify_response,
                  knowledge_graph=knowledge_graph,
                  source_documents=[],
              )
              return None, []
      
      # 步骤5: 使用代理或传统RAG流程
      if self.agent:
          # 通知前端正在思考
          yield ChatEvent(
              event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
              payload=ChatStreamMessagePayload(
                  state=ChatMessageSate.THINKING,
                  display="分析问题并决定如何最佳回答..."
              ),
          )
          
          with self._trace_manager.span(name="agent_reasoning", input=refined_question) as span:
              # 让代理处理查询并生成响应
              try:
                  agent_response = self.agent.chat(refined_question)
                  response_text = str(agent_response)
                  
                  # 记录工具使用情况
                  source_documents = []
                  if hasattr(agent_response, 'sources') and agent_response.sources:
                      tool_calls_for_display = []
                      for tool_call in agent_response.sources:
                          logger.info(f"工具被调用: {tool_call.tool_name}")
                          logger.info(f"工具输入: {tool_call.raw_input}")
                          logger.info(f"工具输出: {tool_call.raw_output}")
                          
                          # 简化展示的工具调用参数
                          if isinstance(tool_call.raw_input, dict) and 'kwargs' in tool_call.raw_input:
                              query_text = tool_call.raw_input['kwargs'].get('natural_language_query', '未指定查询')
                          else:
                              query_text = str(tool_call.raw_input)
                          
                          # 尝试从输出中提取SQL (假设输出格式为"数据库: xxx\n生成的SQL: xxx\n\n结果: xxx")
                          output_str = str(tool_call.raw_output)
                          sql_query = "未提供SQL"
                          if "生成的SQL:" in output_str:
                              sql_parts = output_str.split("生成的SQL:", 1)
                              if len(sql_parts) > 1:
                                  sql_query = sql_parts[1].split("\n\n", 1)[0].strip()
                          
                          # 创建源文档对象
                          source_doc = SourceDocument(
                              id=f"db_tool_{tool_call.tool_name}",
                              title=f"数据库查询: {tool_call.tool_name}",
                              text=f"查询: {query_text}\nSQL: {sql_query}\n结果: {output_str}",
                              metadata={
                                  "tool_name": tool_call.tool_name,
                                  "query": query_text,
                                  "sql": sql_query
                              }
                          )
                          source_documents.append(source_doc)
                          
                          # 为前端准备友好显示
                          tool_call_display = {
                              "tool": tool_call.tool_name.replace("query_", "").replace("_", " "),
                              "query": query_text,
                              "sql": sql_query
                          }
                          tool_calls_for_display.append(tool_call_display)
                      
                      # 向前端发送工具调用信息
                      if tool_calls_for_display:
                          yield ChatEvent(
                              event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                              payload=ChatStreamMessagePayload(
                                  state=ChatMessageSate.TOOL_CALLS,
                                  context=tool_calls_for_display,
                              ),
                          )
                  
                  # 将响应文本分段发送给前端
                  for chunk in response_text.split(". "):
                      if chunk:
                          if not chunk.endswith("."):
                              chunk += ". "
                          yield ChatEvent(
                              event_type=ChatEventType.TEXT_PART,
                              payload=chunk,
                          )
                  
                  span.end(output=response_text)
              except Exception as e:
                  logger.exception(f"代理处理过程中出错: {e}")
                  # 失败时回退到传统RAG流程
                  yield ChatEvent(
                      event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                      payload=ChatStreamMessagePayload(
                          state=ChatMessageSate.ERROR,
                          display="数据库查询过程中出错，尝试使用知识库回答"
                      ),
                  )
                  response_text, source_documents = yield from self._fallback_to_rag(
                      refined_question, knowledge_graph_context
                  )
      else:
          # 如果没有代理，使用传统RAG流程
          response_text, source_documents = yield from self._fallback_to_rag(
              refined_question, knowledge_graph_context
          )
      
      # 步骤6: 完成聊天
      yield from self._chat_finish(
          db_assistant_message=db_assistant_message,
          db_user_message=db_user_message,
          response_text=response_text,
          knowledge_graph=knowledge_graph,
          source_documents=source_documents,
      )
      
      return response_text, source_documents
  
  # 添加回退到传统RAG流程的辅助方法
  def _fallback_to_rag(self, user_question, knowledge_graph_context):
      """当代理处理失败时回退到传统RAG流程"""
      # 搜索相关文档块
      relevant_chunks = yield from self._search_relevance_chunks(user_question)
      
      # 生成回答
      response_text, source_documents = yield from self._generate_answer(
          user_question=user_question,
          knowledge_graph_context=knowledge_graph_context,
          relevant_chunks=relevant_chunks,
      )
      
      return response_text, source_documents
  ```
- **验证方法**：
  - 集成测试：验证代理能正确处理需要数据库查询的问题
  - 失败测试：验证在代理处理失败时能回退到传统RAG流程
  - 用户界面测试：确保工具调用信息正确显示在前端

#### 任务2.3：实现流式输出支持
- **文件位置**：`backend/app/rag/chat/chat_flow.py`
- **实现逻辑**：
  ```python
  # 使用代理的stream_chat方法，替换前一个任务中的agent.chat
  
  async def _agent_stream_chat(self, refined_question):
      """使用代理的stream_chat方法获取流式响应"""
      response_text = ""
      source_documents = []
      tool_calls_for_display = []
      
      stream_events = await self.agent.astream_chat(refined_question)
      try:
          async for event in stream_events:
              # 处理不同类型的事件
              if hasattr(event, 'delta') and event.delta:  # 文本片段
                  delta = event.delta
                  response_text += delta
                  yield ChatEvent(
                      event_type=ChatEventType.TEXT_PART,
                      payload=delta,
                  )
              elif hasattr(event, 'tool_call'):  # 工具调用事件
                  tool_call = event.tool_call
                  logger.info(f"工具被调用: {tool_call.name}")
                  logger.info(f"工具输入: {tool_call.input}")
                  
                  # 提取查询文本
                  query_text = tool_call.input.get('natural_language_query', '未指定查询')
                  
                  # 创建工具调用显示信息
                  tool_call_display = {
                      "tool": tool_call.name.replace("query_", "").replace("_", " "),
                      "query": query_text,
                      "status": "执行中..."
                  }
                  tool_calls_for_display.append(tool_call_display)
                  
                  # 通知前端正在执行数据库查询
                  yield ChatEvent(
                      event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                      payload=ChatStreamMessagePayload(
                          state=ChatMessageSate.TOOL_CALLS,
                          context=tool_calls_for_display,
                      ),
                  )
              elif hasattr(event, 'tool_call_result'):  # 工具调用结果
                  tool_result = event.tool_call_result
                  logger.info(f"工具结果: {tool_result.output}")
                  
                  # 尝试从输出中提取SQL
                  output_str = str(tool_result.output)
                  sql_query = "未提供SQL"
                  if "生成的SQL:" in output_str:
                      sql_parts = output_str.split("生成的SQL:", 1)
                      if len(sql_parts) > 1:
                          sql_query = sql_parts[1].split("\n\n", 1)[0].strip()
                  
                  # 更新工具调用显示信息
                  for call_display in tool_calls_for_display:
                      if call_display["tool"] == tool_result.name.replace("query_", "").replace("_", " "):
                          call_display["status"] = "已完成"
                          call_display["sql"] = sql_query
                  
                  # 创建源文档
                  source_doc = SourceDocument(
                      id=f"db_tool_{tool_result.name}",
                      title=f"数据库查询: {tool_result.name}",
                      text=f"查询: {query_text}\nSQL: {sql_query}\n结果: {output_str}",
                      metadata={
                          "tool_name": tool_result.name,
                          "query": query_text,
                          "sql": sql_query
                      }
                  )
                  source_documents.append(source_doc)
                  
                  # 再次通知前端更新工具调用状态
                  yield ChatEvent(
                      event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                      payload=ChatStreamMessagePayload(
                          state=ChatMessageSate.TOOL_CALLS,
                          context=tool_calls_for_display,
                      ),
                  )
      except Exception as e:
          logger.exception(f"流式处理中出错: {e}")
      
      return response_text, source_documents
  ```
- **验证方法**：
  - 集成测试：验证代理能正确流式输出处理和结果
  - 界面测试：确保前端能正确展示流式回答和工具调用状态

### 阶段三：知识图谱集成与数据库元数据管理（预计工时：3-4天）

#### 任务3.1：创建数据库元数据知识图谱索引流程
- **文件位置**：`backend/app/tasks/knowledge_graph_tasks.py`
- **实现逻辑**：
  ```python
  # knowledge_graph_tasks.py
  import logging
  from typing import List, Dict, Tuple, Optional
  from datetime import datetime
  
  from sqlmodel import Session
  from llama_index.core import KnowledgeGraphIndex, StorageContext
  from llama_index.graph_stores.simple import SimpleGraphStore
  
  from app.core.database import get_session
  from app.models.database_connection import DatabaseConnection
  from app.repositories import database_connection_repo
  
  logger = logging.getLogger(__name__)
  
  def generate_triplets_for_db_connection(db_conn: DatabaseConnection) -> List[Tuple[str, str, str]]:
      """从数据库连接生成知识图谱三元组"""
      triplets = []
      
      # 数据库基本信息
      triplets.append((db_conn.name, "is_a", "Database"))
      triplets.append((db_conn.name, "has_type", db_conn.database_type.value))
      
      if db_conn.description_for_llm:
          triplets.append((db_conn.name, "has_description", db_conn.description_for_llm))
          
      # 表信息
      for table_name, table_desc in db_conn.table_descriptions.items():
          qualified_table_name = f"{db_conn.name}.{table_name}"
          triplets.append((db_conn.name, "contains_table", qualified_table_name))
          triplets.append((qualified_table_name, "is_a", "Table"))
          triplets.append((qualified_table_name, "has_description", table_desc))
          
          # 列信息
          if db_conn.column_descriptions and table_name in db_conn.column_descriptions:
              for col_name, col_desc in db_conn.column_descriptions[table_name].items():
                  qualified_col_name = f"{qualified_table_name}.{col_name}"
                  triplets.append((qualified_table_name, "contains_column", qualified_col_name))
                  triplets.append((qualified_col_name, "is_a", "Column"))
                  triplets.append((qualified_col_name, "has_description", col_desc))
      
      return triplets
  
  def index_database_metadata_to_kg(persist_dir: Optional[str] = "./kg_storage/db_metadata"):
      """将所有数据库连接的元数据索引到知识图谱中"""
      try:
          # 初始化图存储
          graph_store = SimpleGraphStore()
          storage_context = StorageContext.from_defaults(graph_store=graph_store)
          
          # 创建知识图谱索引
          kg_index = KnowledgeGraphIndex(
              [],  # 空节点列表，稍后添加三元组
              storage_context=storage_context,
              index_id="db_metadata_kg"
          )
          
          # 获取所有活跃的数据库连接
          with get_session() as session:
              db_connections = database_connection_repo.get_all_active(session)
              
          total_triplets = 0
          
          # 为每个数据库连接生成并添加三元组
          for db_conn in db_connections:
              try:
                  triplets = generate_triplets_for_db_connection(db_conn)
                  for subj, rel, obj in triplets:
                      kg_index.upsert_triplet((subj, rel, obj))
                  total_triplets += len(triplets)
                  logger.info(f"已为数据库'{db_conn.name}'添加{len(triplets)}个三元组")
              except Exception as e:
                  logger.error(f"处理数据库'{db_conn.name}'时出错: {e}")
          
          # 持久化知识图谱
          if persist_dir:
              kg_index.storage_context.persist(persist_dir=persist_dir)
              logger.info(f"知识图谱已持久化到{persist_dir}")
          
          logger.info(f"数据库元数据知识图谱索引完成，共添加{total_triplets}个三元组")
          return kg_index
      
      except Exception as e:
          logger.exception(f"创建数据库元数据知识图谱失败: {e}")
          raise
  
  # 可以被Celery任务调用的函数
  def update_database_metadata_kg():
      """更新数据库元数据知识图谱（可作为定期任务运行）"""
      logger.info("开始更新数据库元数据知识图谱")
      index_database_metadata_to_kg()
      logger.info("数据库元数据知识图谱更新完成")
  ```
- **验证方法**：
  - 单元测试：验证三元组生成逻辑正确
  - 集成测试：使用测试数据库连接创建小型知识图谱并验证索引过程
  - 存储测试：验证图谱能正确持久化和加载

#### 任务3.2：集成知识图谱查询到ChatFlow
- **文件位置**：`backend/app/rag/tools/knowledge_graph_tools.py`
- **实现逻辑**：
  ```python
  # knowledge_graph_tools.py
  import logging
  import os
  from typing import Optional
  
  from llama_index.core import load_index_from_storage, StorageContext
  from llama_index.core.query_engine import KnowledgeGraphQueryEngine
  from llama_index.core.tools import FunctionTool, ToolMetadata
  from llama_index.core.llms.llm import LLM as LlamaLLM
  
  logger = logging.getLogger(__name__)
  
  def load_db_metadata_kg(persist_dir: str = "./kg_storage/db_metadata"):
      """加载数据库元数据知识图谱"""
      try:
          if not os.path.exists(persist_dir):
              logger.warning(f"知识图谱存储目录{persist_dir}不存在")
              return None
              
          storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
          return load_index_from_storage(storage_context, index_id="db_metadata_kg")
      except Exception as e:
          logger.error(f"加载数据库元数据知识图谱失败: {e}")
          return None
  
  def create_kg_query_tool(kg_index, llm: LlamaLLM) -> Optional[FunctionTool]:
      """创建知识图谱查询工具"""
      if kg_index is None:
          return None
          
      try:
          # 创建查询引擎
          query_engine = KnowledgeGraphQueryEngine(
              kg_index,
              llm=llm,
              verbose=True
          )
          
          # 创建工具函数
          def query_database_metadata(query: str) -> str:
              """
              查询数据库元数据知识图谱
              
              Args:
                  query: 关于数据库、表或列的问题
                  
              Returns:
                  相关数据库元数据信息
              """
              try:
                  response = query_engine.query(query)
                  return str(response)
              except Exception as e:
                  logger.error(f"查询数据库元数据知识图谱失败: {e}")
                  return f"查询失败: {str(e)}"
          
          # 创建工具
          return FunctionTool.from_defaults(
              fn=query_database_metadata,
              name="query_database_metadata",
              description="用于查询可用的数据库、表和列的信息。当你需要了解系统中有哪些数据库，每个数据库包含什么表，或表中有哪些列时使用此工具。"
          )
      except Exception as e:
          logger.error(f"创建知识图谱查询工具失败: {e}")
          return None
  ```
  
  然后在ChatFlow中集成：
  ```python
  # 在ChatFlow.__init__中添加
  from app.rag.tools.knowledge_graph_tools import load_db_metadata_kg, create_kg_query_tool
  
  # 添加到工具初始化部分
  # 加载数据库元数据知识图谱
  db_meta_kg_index = load_db_metadata_kg()
  kg_query_tool = create_kg_query_tool(db_meta_kg_index, self._llm) if db_meta_kg_index else None
  
  # 初始化代理（如果有工具可用）
  all_tools = self.database_query_tools
  if kg_query_tool:
      all_tools.append(kg_query_tool)
      
  if all_tools:
      self.agent = OpenAIAgent.from_tools(
          tools=all_tools,
          llm=self._llm,
          verbose=True,
          system_prompt="""你是一个智能助手，可以通过提供的工具查询数据库和数据库元数据。
          根据用户问题，判断是否需要查询数据库来回答。
          如果用户询问关于可用数据库、表或列的信息，请使用query_database_metadata工具查询。
          如果需要查询特定数据库数据，请使用对应的数据库查询工具。
          基于查询结果提供准确的回答，并在合适时引用数据来源。
          如果涉及多个工具，先了解数据结构再进行查询。
          """
      )
  else:
      self.agent = None
  ```
- **验证方法**：
  - 集成测试：验证加载知识图谱和创建查询工具的流程
  - 功能测试：验证代理能使用知识图谱工具回答关于数据库结构的问题

#### 任务3.3：创建定期更新数据库元数据的Celery任务
- **文件位置**：`backend/app/tasks/celery_tasks.py`
- **实现逻辑**：
  ```python
  # 在现有Celery任务文件中添加
  from celery import shared_task
  from app.tasks.knowledge_graph_tasks import update_database_metadata_kg
  
  @shared_task(name="update_database_metadata_kg")
  def celery_update_database_metadata_kg():
      """更新数据库元数据知识图谱的Celery任务"""
      update_database_metadata_kg()
  ```
  

配置定期执行的Celery任务：
```python
# backend/app/core/celery_config.py
from celery.schedules import crontab

# 现有配置...

# 添加数据库元数据知识图谱更新任务到定期任务
CELERYBEAT_SCHEDULE = {
    # 其他现有定期任务...
    'update_database_metadata_kg': {
        'task': 'update_database_metadata_kg',
        'schedule': crontab(hour=3, minute=30),  # 每天凌晨3:30执行
        'options': {'queue': 'bg_tasks'},
    },
}
```
- **验证方法**：
  - 手动触发任务并验证执行结果
  - 检查日志确认定时执行正常

### 阶段四：前端界面增强（预计工时：3-4天）

#### 任务4.1：增强聊天界面以展示数据库查询信息
- **文件位置**：前端相关文件
- **实现逻辑**：
  ```typescript
  // 在前端Chat组件中
  
  // 添加处理TOOL_CALLS事件的逻辑
  const handleChatEvent = (event) => {
    if (event.type === 'TOOL_CALLS') {
      // 设置工具调用状态
      setToolCalls(event.payload.context);
    }
    // 其他现有事件处理...
  };
  
  // 添加数据库查询结果展示组件
  const DatabaseQueryResult = ({ toolCall }) => {
    return (
      <div className="database-query-result">
        <div className="query-header">
          <span className="database-name">{toolCall.tool}</span>
          <span className="query-status">{toolCall.status || '已完成'}</span>
        </div>
        <div className="query-content">
          <div className="query-text">
            <span className="label">问题：</span>
            <span>{toolCall.query}</span>
          </div>
          {toolCall.sql && (
            <div className="query-sql">
              <span className="label">SQL：</span>
              <pre>{toolCall.sql}</pre>
              <button className="copy-button" onClick={() => copyToClipboard(toolCall.sql)}>
                复制SQL
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };
  
  // 在消息渲染时，检查是否有工具调用
  const renderMessage = (message) => {
    return (
      <div className="message">
        {message.content}
        
        {message.toolCalls && message.toolCalls.length > 0 && (
          <div className="tool-calls-container">
            <h4>数据库查询</h4>
            {message.toolCalls.map((toolCall, index) => (
              <DatabaseQueryResult key={index} toolCall={toolCall} />
            ))}
          </div>
        )}
      </div>
    );
  };
  ```
- **验证方法**：
  - 用户界面测试：验证工具调用信息正确显示
  - 交互测试：验证复制SQL功能正常工作

#### 任务4.2：增加数据库查询历史视图
- **文件位置**：前端相关文件
- **实现逻辑**：
  ```typescript
  // 创建数据库查询历史组件
  
  // 获取查询历史数据的API函数
  const fetchDatabaseQueryHistory = async (chatId) => {
    const response = await fetch(`/api/chats/${chatId}/database/queries`);
    if (!response.ok) {
      throw new Error('获取数据库查询历史失败');
    }
    return response.json();
  };
  
  // 历史记录组件
  const DatabaseQueryHistory = ({ chatId }) => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    
    useEffect(() => {
      const loadHistory = async () => {
        try {
          setLoading(true);
          const data = await fetchDatabaseQueryHistory(chatId);
          setHistory(data);
        } catch (err) {
          setError(err.message);
        } finally {
          setLoading(false);
        }
      };
      
      loadHistory();
    }, [chatId]);
    
    if (loading) return <div>加载中...</div>;
    if (error) return <div>错误: {error}</div>;
    
    return (
      <div className="query-history">
        <h3>数据库查询历史</h3>
        {history.length === 0 ? (
          <p>暂无查询历史</p>
        ) : (
          <ul className="history-list">
            {history.map(query => (
              <li key={query.id} className="history-item">
                <div className="history-header">
                  <span className="database">{query.database_name}</span>
                  <span className="timestamp">{new Date(query.created_at).toLocaleString()}</span>
                </div>
                <div className="history-query">{query.nl_query}</div>
                <div className="history-sql">
                  <pre>{query.sql_query}</pre>
                  <button onClick={() => copyToClipboard(query.sql_query)}>
                    复制SQL
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  };
  ```
- **验证方法**：
  - API测试：验证历史记录API正确返回数据
  - 界面测试：确保历史记录组件正确显示和交互

#### 任务4.3：添加数据库查询反馈功能
- **文件位置**：前端和后端相关文件
- **实现逻辑**：
  ```typescript
  // 前端查询反馈组件
  const QueryFeedback = ({ queryId }) => {
    const [rating, setRating] = useState(0);
    const [feedback, setFeedback] = useState('');
    const [submitted, setSubmitted] = useState(false);
    
    const handleSubmit = async () => {
      try {
        const response = await fetch(`/api/database/queries/${queryId}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ rating, feedback }),
        });
        
        if (response.ok) {
          setSubmitted(true);
        }
      } catch (error) {
        console.error('提交反馈失败:', error);
      }
    };
    
    if (submitted) {
      return <div className="feedback-success">感谢您的反馈！</div>;
    }
    
    return (
      <div className="query-feedback">
        <h4>这个查询结果有帮助吗？</h4>
        <div className="rating">
          {[1, 2, 3, 4, 5].map(star => (
            <button
              key={star}
              className={`star ${rating >= star ? 'active' : ''}`}
              onClick={() => setRating(star)}
            >
              ★
            </button>
          ))}
        </div>
        <textarea
          placeholder="您有什么建议能帮助我们改进？（可选）"
          value={feedback}
          onChange={e => setFeedback(e.target.value)}
        ></textarea>
        <button 
          className="submit-button"
          onClick={handleSubmit}
          disabled={rating === 0}
        >
          提交反馈
        </button>
      </div>
    );
  };
  ```
  
  后端API端点：
  ```python
  # backend/app/api/routes/database.py
  from fastapi import APIRouter, Depends, HTTPException, status
  from pydantic import BaseModel
  from typing import Optional
  
  from app.models import User
  from app.api.deps import get_current_user, get_db_session
  from app.repositories import database_query_history_repo
  
  router = APIRouter(prefix="/database", tags=["database"])
  
  class QueryFeedbackModel(BaseModel):
      rating: int
      feedback: Optional[str] = None
  
  @router.post("/queries/{query_id}/feedback", status_code=status.HTTP_200_OK)
  def submit_query_feedback(
      query_id: int,
      feedback: QueryFeedbackModel,
      session = Depends(get_db_session),
      current_user: User = Depends(get_current_user),
  ):
      """提交数据库查询反馈"""
      query_history = database_query_history_repo.get(session, query_id)
      
      if not query_history:
          raise HTTPException(
              status_code=status.HTTP_404_NOT_FOUND,
              detail=f"未找到ID为{query_id}的查询历史",
          )
      
      # 检查用户是否有权限提交反馈（应该是查询的创建者）
      if query_history.user_id != current_user.id:
          raise HTTPException(
              status_code=status.HTTP_403_FORBIDDEN,
              detail="您没有权限为此查询提交反馈",
          )
      
      # 更新查询历史
      query_history.user_rating = feedback.rating
      query_history.user_feedback = feedback.feedback
      
      session.add(query_history)
      session.commit()
      
      return {"message": "反馈提交成功"}
  ```
- **验证方法**：
  - API测试：验证反馈提交端点正确工作
  - 界面测试：确保反馈组件正确显示和提交数据

### 阶段五：测试、优化和部署（预计工时：3-4天）

#### 任务5.1：编写集成测试
- **文件位置**：`backend/tests/test_database_tools.py`和`backend/tests/test_chat_flow_db_tools.py`
- **实现逻辑**：
  ```python
  # test_database_tools.py
  import unittest
  from unittest.mock import MagicMock, patch
  
  from app.models.database_connection import DatabaseConnection, DatabaseType
  from app.rag.tools.database_tools import (
      create_llama_sql_database_from_connection,
      create_database_function_tool,
      test_database_connection
  )
  
  class TestDatabaseTools(unittest.TestCase):
      def test_create_llama_sql_database_from_connection(self):
          # 创建模拟数据库连接对象
          db_conn = MagicMock(spec=DatabaseConnection)
          db_conn.name = "测试数据库"
          db_conn.database_type = DatabaseType.SQLITE
          db_conn.config = {"file_path": ":memory:"}
          db_conn.table_descriptions = {"users": "用户表"}
          
          # 测试创建LlamaIndex SQLDatabase
          with patch("app.rag.tools.database_tools.create_engine") as mock_create_engine:
              mock_engine = MagicMock()
              mock_create_engine.return_value = mock_engine
              
              with patch("app.rag.tools.database_tools.SQLDatabase") as mock_sql_database:
                  create_llama_sql_database_from_connection(db_conn)
                  
                  # 验证调用
                  mock_create_engine.assert_called_once_with("sqlite:///:memory:")
                  mock_sql_database.assert_called_once_with(
                      mock_engine, include_tables=["users"]
                  )
      
      # 其他测试方法...
  
  # test_chat_flow_db_tools.py
  # 集成测试，涉及数据库查询工具在ChatFlow中的使用
  ```
- **验证方法**：
  - 运行单元测试并验证通过
  - 运行集成测试并验证数据库工具在ChatFlow中正常工作

#### 任务5.2：性能优化
- **实现逻辑**：
  ```python
  # 在database_tools.py中添加连接池管理
  from sqlalchemy.pool import QueuePool
  
  # 全局引擎缓存
  _engines_cache = {}
  
  def get_engine_for_db_connection(db_conn: DatabaseConnection):
      """获取或创建数据库连接的引擎，使用连接池"""
      cache_key = f"{db_conn.id}_{db_conn.updated_at.isoformat()}"
      
      if cache_key in _engines_cache:
          return _engines_cache[cache_key]
      
      # 构建连接字符串
      connection_string = build_connection_string(db_conn)
      
      # 创建引擎，配置连接池
      engine = create_engine(
          connection_string,
          poolclass=QueuePool,
          pool_size=5,        # 初始连接数
          max_overflow=10,    # 允许的最大连接数
          pool_timeout=30,    # 等待连接的超时时间（秒）
          pool_recycle=1800   # 重用连接的时间（秒）
      )
      
      _engines_cache[cache_key] = engine
      return engine
  ```
- **验证方法**：
  - 负载测试：模拟多个用户同时发送需要数据库查询的问题
  - 监控：观察连接池状态和系统资源使用情况

#### 任务5.3：监控和日志增强
- **文件位置**：多个现有文件
- **实现逻辑**：
  ```python
  # 在database_tools.py中增强日志记录
  import time
  
  def query_database(natural_language_query: str) -> str:
      """查询数据库函数"""
      try:
          logger.info(f"执行数据库查询: {natural_language_query}")
          start_time = time.time()
          
          response = query_engine.query(natural_language_query)
          
          execution_time = time.time() - start_time
          sql_query = response.metadata.get("sql_query", "未生成SQL")
          result = str(response)
          
          logger.info(f"查询完成，耗时: {execution_time:.3f}秒, SQL: {sql_query}")
          
          # 记录查询指标
          metrics = {
              "execution_time": execution_time,
              "query_length": len(natural_language_query),
              "result_size": len(result),
              "database_name": db_conn.name,
              "database_type": db_conn.database_type.value
          }
          
          # 如果有Prometheus或其他监控系统，记录指标
          if hasattr(settings, "METRICS_ENABLED") and settings.METRICS_ENABLED:
              record_metrics("database_query", metrics)
          
          return f"数据库: {db_conn.name}\n生成的SQL: {sql_query}\n\n结果: {result}"
      except Exception as e:
          logger.error(f"数据库查询失败: {e}")
          return f"数据库查询失败: {str(e)}"
  ```
- **验证方法**：
  - 检查日志输出确保包含所有必要信息
  - 验证监控指标正确记录到监控系统

#### 任务5.4：部署计划编写
- **文件位置**：`./deployment_guide.md`
- **实现逻辑**：
  ```markdown
  # 数据库智能查询功能部署指南
  
  本文档详细说明如何在生产环境部署和配置数据库智能查询功能。
  
  ## 系统要求
  
  - Python 3.9+
  - 大模型访问（支持function calling的OpenAI模型如GPT-4）
  - TiDB或其他支持的数据库系统
  
  ## 部署步骤
  
  1. **更新代码库**
     - 将新代码合并到主分支
     - 在生产服务器上拉取最新代码
  
  2. **安装依赖**
     ```bash
     pip install llama-index sqlalchemy mysql-connector-python
     ```
  
  3. **配置环境变量**
     ```bash
     # 在.env文件中添加
     OPENAI_API_KEY=your_api_key
     METRICS_ENABLED=true
     DB_METADATA_KG_DIR=/path/to/kg_storage
     ```
  
  4. **初始化知识图谱**
     ```bash
     python -m app.tasks.knowledge_graph_tasks
     ```
  
  5. **配置Celery定期任务**
     - 确保celery worker和beat服务已启动
     - 验证定期任务是否正常执行
  
  6. **验证部署**
     - 测试几个需要数据库查询的对话
     - 检查日志确认工具调用正常
     - 验证前端正确显示查询结果
  
  ## 回滚计划
  
  若部署出现问题，执行以下步骤回滚：
  
  1. 恢复之前版本的代码
  2. 重启服务
  3. 临时禁用数据库查询功能（通过配置）
  ```
- **验证方法**：
  - 在测试环境按照部署指南完成部署流程
  - 验证所有功能在部署后正常工作

## 二、项目时间和资源估计

### 总体时间线

- **阶段一（数据库工具创建基础设施）**: 3-4个工作日
- **阶段二（集成到Chat Flow）**: 4-5个工作日
- **阶段三（知识图谱集成与数据库元数据管理）**: 3-4个工作日
- **阶段四（前端界面增强）**: 3-4个工作日
- **阶段五（测试、优化和部署）**: 3-4个工作日

**总计预估工时**: 16-21个工作日（约3-4周）

### 资源需求

- **开发人员**: 
  - 1名后端开发工程师（Python/FastAPI/LlamaIndex专业知识）
  - 1名前端开发工程师（React/TypeScript专业知识）
  - 建议有0.5名熟悉数据库系统和SQL的工程师参与（可以是上述开发者之一）

- **基础设施**:
  - 开发和测试环境服务器
  - 带向量支持的TiDB数据库
  - OpenAI API访问（支持function calling的模型）
  
- **开发工具**:
  - 代码版本控制系统（Git）
  - 项目管理工具
  - 日志和监控系统

## 三、风险评估和缓解策略

| 风险 | 影响 | 可能性 | 缓解策略 |
|------|------|--------|----------|
| LLM理解数据库结构不准确 | 高 | 中 | 1. 使用结构化的表和列描述<br>2. 优化工具描述模板<br>3. 使用更强大的LLM如GPT-4 |
| 数据库查询性能问题 | 高 | 中 | 1. 连接池管理<br>2. 添加超时机制<br>3. 监控和优化常见查询模式 |
| SQL注入风险 | 高 | 低 | 1. 确保LlamaIndex NLSQLTableQueryEngine正确处理参数<br>2. 为测试数据库使用只读用户<br>3. 定期审查生成的SQL |
| AI回复结构化数据不一致 | 中 | 高 | 1. 使用结构化查询结果模板<br>2. 自定义响应后处理逻辑<br>3. 增加后验验证 |
| API成本增加 | 中 | 高 | 1. 实现查询缓存机制<br>2. 优化提示以减少token使用<br>3. 设置费用监控和预算警报 |
| 用户反馈不满意 | 中 | 中 | 1. A/B测试不同提示模板<br>2. 收集并分析用户反馈<br>3. 创建错误处理改进机制 |

## 四、验收标准

功能完成后，应满足以下验收标准：

1. **功能完整性**:
   - 能够基于现有数据库连接配置自动创建查询工具
   - LLM能正确决定何时需要查询数据库
   - 查询结果能准确展示在聊天界面中
   - 数据库元数据能正确存储在知识图谱中并被查询

2. **性能标准**:
   - 数据库工具创建过程应在2秒内完成
   - 查询执行（不含LLM思考时间）应在5秒内返回结果
   - 系统能同时处理至少10个并发数据库查询
   - 知识图谱查询响应时间应不超过1秒

3. **质量标准**:
   - 代码通过所有单元测试和集成测试
   - 代码遵循项目编码规范
   - 代码有注释和文档字符串
   - 所有功能有用户文档和开发者指南

4. **安全标准**:
   - 数据库连接信息安全存储
   - 查询结果尊重用户权限
   - 无SQL注入风险
   - 敏感信息不在日志中明文显示

## 五、未来扩展机会

1. **高级查询功能**:
   - 支持跨数据库查询
   - 支持自然语言定义复杂过滤条件
   - 支持数据可视化生成

2. **工具链增强**:
   - 动态SQL调优建议
   - 自动生成数据模型架构图
   - 支持基于查询历史的相似查询推荐

3. **用户体验提升**:
   - 允许用户修改生成的SQL
   - 提供查询执行计划分析
   - 支持将查询保存为视图或报表

4. **集成扩展**:
   - 与BI工具集成
   - 支持更多数据库类型
   - 支持更多LLM提供商

通过此项目，AutoFlow将获得强大的数据库查询和分析能力，为用户提供更加智能和直观的数据交互体验。

## 实施进度总结

### 已完成任务 (2023年6月10日)

1. **✅ 阶段一：核心功能开发**
   - 完成了ChatEngineConfig的增强，支持关联数据库连接
   - 创建了数据库工具工厂模块，支持从数据库连接创建LlamaIndex工具
   - 集成了工具调用到ChatFlow，实现了大模型自主判断和调用数据库查询
   - 所有单元测试和集成测试均已通过，功能可用

### 正在进行的任务

1. **🔄 阶段二：用户界面集成**
   - 设计并实现数据库连接配置界面
   - 增强聊天界面以显示数据库查询过程和结果
   - 添加工具调用可视化功能

### 下一步计划

1. **阶段三：知识图谱集成**
   - 实现数据库元数据到知识图谱的转换
   - 开发数据库结构可视化功能
   - 利用知识图谱增强数据库查询理解和执行

## 验证与测试结果

为确保功能的稳定性和可靠性，我们已编写并执行了以下测试，所有测试均已通过：

1. **单元测试**
   - `tests/test_chat_engine_config.py`: 测试ChatEngineConfig关联数据库连接
   - `tests/test_database_tools.py`: 测试数据库工具工厂模块
   - `tests/test_chat_flow_database_tools.py`: 测试ChatFlow数据库工具集成

2. **集成测试**
   - 使用了模拟数据库连接进行工具创建和调用测试
   - 验证了决策逻辑在不同情况下的正确性
   - 测试了多种数据库查询场景下的系统响应

系统已具备基础的数据库智能查询能力，用户可以通过自然语言提问，系统能够判断是否需要查询数据库并执行相应操作。下一步将进一步优化查询精度和用户体验。
