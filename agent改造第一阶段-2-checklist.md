
# 基于LlamaIndex工作流的Agent改造计划

## 一、问题诊断

当前系统从固定流程的`chat_flow.py`改为智能体模式的`autoflow_agent.py`后遇到的核心问题:

1. **事件类型不匹配**：前端期望的事件类型与Agent产生的事件类型不一致
2. **工具调用格式问题**：工具返回格式不符合LlamaIndex的要求
3. **流程控制难题**：Agent模式下难以实现原固定流程的精确控制

## 二、工作流架构设计

基于LlamaIndex Workflow for a ReAct Agent的思路，我们可以设计更灵活且可控的工作流架构：

```
┌─────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌───────────────┐
│  InputProcessor │────▶│ KnowledgeAgent │────▶│ ReasoningAgent │────▶│ ResponseAgent │
└─────────────────┘     └────────────────┘     └────────────────┘     └───────────────┘
        │                      │                      │                      │
        ▼                      ▼                      ▼                      ▼
┌─────────────────┐     ┌────────────────┐     ┌────────────────┐     ┌───────────────┐
│  QueryRefiner   │     │ KnowledgeBase  │     │ LogicalAnalysis│     │ResponseSynth  │
│  Tools          │     │ KnowledgeGraph │     │ DeepResearch   │     │Formatting     │
│                 │     │ Tools          │     │ Tools          │     │Tools          │
└─────────────────┘     └────────────────┘     └────────────────┘     └───────────────┘
```

## 三、工作流事件定义

```python
class PrepEvent(Event):
    """准备事件，用于启动或循环工作流"""
    pass

class InputEvent(Event):
    """输入事件，包含用户输入和聊天历史"""
    input: list[ChatMessage]

class KnowledgeEvent(Event):
    """知识检索事件，包含从知识库和知识图谱检索的结果"""
    knowledge_nodes: List[Dict]
    knowledge_graph_context: str

class ReasoningEvent(Event):
    """推理事件，包含Agent的推理过程和决策"""
    reasoning: List[Any]
    tool_calls: Optional[List[ToolSelection]] = None

class ResponseEvent(Event):
    """响应事件，包含最终生成的回答"""
    response: str
    sources: List[Any]

class StreamEvent(Event):
    """流式输出事件，包含增量文本"""
    delta: str
```

## 四、工作流步骤实现

### 1. 输入处理工作流

```python
@step
async def process_input(
    self, ctx: Context, ev: Union[StartEvent, InputEvent]
) -> Union[PrepEvent, KnowledgeEvent]:
    """处理用户输入，执行问题优化和改写"""
    
    # 获取用户问题和聊天历史
    if isinstance(ev, StartEvent):
        chat_history = await ctx.get("chat_history", [])
        user_question = await ctx.get("user_question", "")
    else:
        chat_history = ev.input[:-1]
        user_question = ev.input[-1].content
    
    # 创建初始聊天消息记录
    user_message, assistant_message = self._create_chat_messages(
        user_question, chat_history
    )
    await ctx.set("db_user_message", user_message)
    await ctx.set("db_assistant_message", assistant_message)
    
    # 发送前端事件
    self._emit_event(ChatEventType.DATA_PART, {...})
    
    # 执行问题优化/改写 (基于配置决定是否执行)
    if self.engine_config.query_optimization_enabled:
        refined_question = await self._refine_question(user_question, chat_history)
        await ctx.set("refined_question", refined_question)
    else:
        await ctx.set("refined_question", user_question)
    
    # 执行问题澄清判断 (基于配置决定是否执行)
    if self.engine_config.clarify_question:
        need_clarify, clarify_msg = await self._check_question_clarity(
            await ctx.get("refined_question"), chat_history
        )
        if need_clarify:
            # 返回澄清请求并结束工作流
            self._emit_event(ChatEventType.TEXT_PART, clarify_msg)
            return StopEvent(result={"response": clarify_msg, "sources": []})
    
    # 继续进入知识检索阶段
    return PrepEvent()
```

### 2. 知识检索工作流

```python
@step
async def retrieve_knowledge(
    self, ctx: Context, ev: PrepEvent
) -> KnowledgeEvent:
    """执行知识库检索和知识图谱查询"""
    
    # 获取优化后的问题
    refined_question = await ctx.get("refined_question")
    
    # 发送知识检索状态事件
    self._emit_event(
        ChatEventType.MESSAGE_ANNOTATIONS_PART,
        {"state": ChatMessageSate.SEARCH_RELATED_DOCUMENTS, "display": "检索相关知识..."}
    )
    
    # 并行执行知识库检索和知识图谱查询
    knowledge_nodes = []
    knowledge_graph_context = ""
    
    # 检索知识库
    if self.engine_config.vector_search.enabled:
        knowledge_result = await self._retrieve_knowledge_base(refined_question)
        knowledge_nodes = knowledge_result
        
        # 发送知识检索结果事件
        self._emit_event(
            ChatEventType.MESSAGE_ANNOTATIONS_PART,
            {"state": ChatMessageSate.SOURCE_NODES, "context": knowledge_nodes}
        )
    
    # 查询知识图谱
    if self.engine_config.knowledge_graph.enabled:
        kg_result, kg_context = await self._query_knowledge_graph(refined_question)
        knowledge_graph_context = kg_context
    
    # 记录检索结果
    await ctx.set("knowledge_nodes", knowledge_nodes)
    await ctx.set("knowledge_graph_context", knowledge_graph_context)
    
    # 返回知识事件
    return KnowledgeEvent(
        knowledge_nodes=knowledge_nodes,
        knowledge_graph_context=knowledge_graph_context
    )
```

### 3. 推理分析工作流

```python
@step
async def analyze_and_reason(
    self, ctx: Context, ev: KnowledgeEvent
) -> Union[ReasoningEvent, ResponseEvent]:
    """执行推理分析，根据需要调用专业工具"""
    
    # 获取问题和知识
    refined_question = await ctx.get("refined_question")
    knowledge_nodes = ev.knowledge_nodes
    knowledge_graph_context = ev.knowledge_graph_context
    
    # 发送推理状态事件
    self._emit_event(
        ChatEventType.MESSAGE_ANNOTATIONS_PART,
        {"state": ChatMessageSate.GENERATE_ANSWER, "display": "分析信息中..."}
    )
    
    # 初始化推理步骤
    reasoning_steps = []
    
    # 使用LLM分析知识和问题
    analysis_result = await self._analyze_knowledge(
        refined_question, knowledge_nodes, knowledge_graph_context
    )
    reasoning_steps.append({"type": "analysis", "content": analysis_result})
    
    # 判断是否需要深度研究
    if self.engine_config.deep_research_enabled and self._needs_deep_research(analysis_result):
        deep_research_result = await self._perform_deep_research(
            refined_question, analysis_result
        )
        reasoning_steps.append({"type": "deep_research", "content": deep_research_result})
    
    # 判断是否需要数据库查询
    if self.engine_config.sql_query_enabled and self._needs_database_query(analysis_result):
        sql_query_result = await self._perform_sql_query(refined_question)
        reasoning_steps.append({"type": "sql_query", "content": sql_query_result})
    
    # 提前确定是否需要工具调用
    needs_tool = self._determine_if_needs_tool(reasoning_steps)
    
    # 如果需要工具调用，返回推理事件继续工作流
    if needs_tool:
        tool_calls = self._prepare_tool_calls(reasoning_steps)
        return ReasoningEvent(reasoning=reasoning_steps, tool_calls=tool_calls)
    
    # 否则直接生成最终回答
    final_response = await self._synthesize_response(
        refined_question, knowledge_nodes, knowledge_graph_context, reasoning_steps
    )
    
    # 返回响应事件
    return ResponseEvent(response=final_response, sources=knowledge_nodes)
```

### 4. 工具调用工作流

```python
@step
async def handle_tool_calls(
    self, ctx: Context, ev: ReasoningEvent
) -> Union[PrepEvent, ResponseEvent]:
    """处理工具调用请求"""
    
    # 如果没有工具调用请求，直接准备下一步
    if not ev.tool_calls:
        return PrepEvent()
    
    # 初始化工具映射
    tools_map = {tool.metadata.name: tool for tool in self.tools}
    
    # 记录当前推理步骤
    reasoning_steps = ev.reasoning
    
    # 处理每个工具调用
    for i, tool_call in enumerate(ev.tool_calls):
        tool_id = str(i + 1)
        tool_name = tool_call.tool_name
        tool_args = tool_call.tool_kwargs
        
        # 发送工具调用事件
        self._emit_event(
            ChatEventType.TOOL_CALL_PART if hasattr(ChatEventType, "TOOL_CALL_PART") 
            else ChatEventType.MESSAGE_ANNOTATIONS_PART,
            {
                "toolCallId": tool_id,
                "toolName": tool_name,
                "args": tool_args
            }
        )
        
        # 执行工具调用
        if tool_name in tools_map:
            try:
                tool_result = tools_map[tool_name](**tool_args)
                
                # 添加工具结果到推理步骤
                reasoning_steps.append({
                    "type": "tool_result",
                    "tool": tool_name,
                    "result": tool_result
                })
                
                # 发送工具结果事件
                self._emit_event(
                    ChatEventType.TOOL_RESULT_PART if hasattr(ChatEventType, "TOOL_RESULT_PART") 
                    else ChatEventType.MESSAGE_ANNOTATIONS_PART,
                    {
                        "toolCallId": tool_id,
                        "result": tool_result
                    }
                )
            except Exception as e:
                # 处理工具调用异常
                reasoning_steps.append({
                    "type": "tool_error",
                    "tool": tool_name,
                    "error": str(e)
                })
    
    # 更新推理步骤
    await ctx.set("reasoning_steps", reasoning_steps)
    
    # 判断是否需要继续推理
    if self._needs_further_reasoning(reasoning_steps):
        return PrepEvent()  # 返回到分析推理步骤继续处理
    else:
        # 生成最终回答
        refined_question = await ctx.get("refined_question")
        knowledge_nodes = await ctx.get("knowledge_nodes")
        knowledge_graph_context = await ctx.get("knowledge_graph_context")
        
        final_response = await self._synthesize_response(
            refined_question, knowledge_nodes, knowledge_graph_context, reasoning_steps
        )
        
        return ResponseEvent(response=final_response, sources=knowledge_nodes)
```

### 5. 回答生成工作流

```python
@step
async def generate_response(
    self, ctx: Context, ev: Union[ReasoningEvent, ResponseEvent]
) -> StopEvent:
    """生成最终回答并完成对话"""
    
    # 获取回答内容
    if isinstance(ev, ResponseEvent):
        response_text = ev.response
        source_documents = ev.sources
    else:
        # 如果是从推理事件传入，需要生成回答
        refined_question = await ctx.get("refined_question")
        knowledge_nodes = await ctx.get("knowledge_nodes", [])
        knowledge_graph_context = await ctx.get("knowledge_graph_context", "")
        reasoning_steps = ev.reasoning
        
        response_text = await self._synthesize_response(
            refined_question, knowledge_nodes, knowledge_graph_context, reasoning_steps
        )
        source_documents = knowledge_nodes
    
    # 发送生成回答状态事件
    self._emit_event(
        ChatEventType.MESSAGE_ANNOTATIONS_PART,
        {"state": ChatMessageSate.GENERATE_ANSWER, "display": "生成最终回答..."}
    )
    
    # 流式输出回答
    for chunk in self._stream_response(response_text):
        self._emit_event(ChatEventType.TEXT_PART, chunk)
    
    # 完成对话并保存结果
    db_user_message = await ctx.get("db_user_message")
    db_assistant_message = await ctx.get("db_assistant_message")
    
    self._complete_chat(
        db_user_message,
        db_assistant_message,
        response_text,
        source_documents
    )
    
    # 发送完成状态事件
    self._emit_event(
        ChatEventType.MESSAGE_ANNOTATIONS_PART,
        {"state": ChatMessageSate.FINISHED, "message": "回答完成"}
    )
    
    # 结束工作流并返回结果
    return StopEvent(
        result={
            "response": response_text,
            "sources": source_documents,
            "reasoning": await ctx.get("reasoning_steps", [])
        }
    )
```

## 五、主工作流组装

```python
class AgentWorkflow:
    """主Agent工作流，组合各个步骤"""
    
    def __init__(
        self,
        db_session: Session,
        user: User,
        browser_id: str,
        engine_config: ChatEngineConfig,
        tools: List[BaseTool],
        llm: LLM
    ):
        self.db_session = db_session
        self.user = user
        self.browser_id = browser_id
        self.engine_config = engine_config
        self.tools = tools
        self.llm = llm
        
        # 创建工作流处理器
        self.workflow = Workflow()
        
        # 注册工作流步骤
        self._register_workflow_steps()
    
    def _register_workflow_steps(self):
        """注册所有工作流步骤"""
        input_processor = InputProcessor(self.db_session, self.engine_config)
        knowledge_agent = KnowledgeAgent(self.db_session, self.engine_config)
        reasoning_agent = ReasoningAgent(self.db_session, self.engine_config, self.tools)
        response_agent = ResponseAgent(self.db_session, self.engine_config)
        
        # 注册步骤处理器
        self.workflow.add_step(StartEvent, input_processor.process_input)
        self.workflow.add_step(PrepEvent, knowledge_agent.retrieve_knowledge)
        self.workflow.add_step(KnowledgeEvent, reasoning_agent.analyze_and_reason)
        self.workflow.add_step(ReasoningEvent, reasoning_agent.handle_tool_calls)
        self.workflow.add_step(ResponseEvent, response_agent.generate_response)
    
    async def run(self, user_question: str, chat_history: List[ChatMessage] = None):
        """运行工作流处理用户问题"""
        ctx = Context(self.workflow)
        
        # 设置初始上下文
        await ctx.set("user_question", user_question)
        await ctx.set("chat_history", chat_history or [])
        
        # 启动工作流
        handler = self.workflow.start(ctx=ctx)
        
        # 处理工作流事件流
        async for event in handler.stream_events():
            if isinstance(event, StreamEvent):
                # 直接发送流式文本块
                yield event.delta
            elif hasattr(event, 'event_type') and hasattr(event, 'payload'):
                # 转发格式化的前端事件
                yield event
        
        # 等待工作流完成并获取最终结果
        result = await handler
        return result
```

## 六、事件兼容性处理

我们需要一个事件转换层，确保工作流产生的事件与前端期望的事件格式兼容：

```python
class EventEmitter:
    """事件发射器，处理事件转换和发送"""
    
    @staticmethod
    def emit(event_type: ChatEventType, payload: Any) -> ChatEvent:
        """发射标准化的事件"""
        
        # 修复缺失的事件类型
        if not hasattr(ChatEventType, "TOOL_CALL_PART") and event_type == "TOOL_CALL_PART":
            event_type = ChatEventType.MESSAGE_ANNOTATIONS_PART
        
        if not hasattr(ChatEventType, "TOOL_RESULT_PART") and event_type == "TOOL_RESULT_PART":
            event_type = ChatEventType.MESSAGE_ANNOTATIONS_PART
        
        # 根据事件类型处理payload
        if isinstance(payload, dict) and "state" in payload:
            payload = ChatStreamMessagePayload(**payload)
        
        return ChatEvent(event_type=event_type, payload=payload)
```

## 七、改造路线图

### 阶段一：基础架构改造（1-2周）

1. **创建工作流基础架构**
   - 实现Event类定义
   - 实现Context管理
   - 实现Step装饰器和注册机制

2. **实现核心工作流框架**
   - 实现工作流引擎
   - 实现事件处理和转发
   - 添加错误处理和恢复机制

### 阶段二：单元模块开发（2-3周）

1. **开发独立Agent模块**
   - 输入处理Agent
   - 知识检索Agent
   - 推理分析Agent
   - 回答生成Agent

2. **工具适配和集成**
   - 确保所有工具返回ToolOutput格式
   - 实现工具映射和调用接口
   - 添加工具调用监控和日志

### 阶段三：系统集成与优化（1-2周）

1. **工作流组装和测试**
   - 整合所有Agent模块
   - 添加端到端测试
   - 实现事件流处理和兼容性

2. **前端接口适配**
   - 确保事件格式兼容
   - 实现流式响应
   - 处理前端状态更新

### 阶段四：部署与监控（1周）

1. **系统部署**
   - 部署新工作流系统
   - 实现旧系统到新系统的平滑迁移
   - A/B测试对比效果

2. **监控与反馈**
   - 添加性能监控
   - 实现日志分析
   - 收集用户反馈并迭代优化

## 八、预期优势

1. **模块化与可扩展性**：每个Agent关注特定职责，便于维护和扩展
2. **灵活的工具集成**：各Agent可以有自己的工具集，按需使用
3. **流程可配置**：可以根据配置动态启用或禁用特定Agent或工具
4. **更好的错误处理**：子工作流出错不会影响整体，便于故障恢复
5. **事件流标准化**：确保前端收到一致的事件格式，提高兼容性

通过工作流的方式重构Agent模块，我们能保留固定流程的可控性同时享受智能Agent的灵活性，真正结合两者优势，打造更强大、更稳定的AI应用。
