---
description: 
globs: 
alwaysApply: false
---

# ChatEvent 开发使用手册 - 后端篇

## 一、核心概念与架构

### 1. ChatEvent 类型定义

ChatEvent 是后端向前端传递状态和信息的标准方式。在 `types.py` 中定义了 `ChatEventType` 枚举，表示不同类型的事件：

```python
# backend/app/rag/types.py
class ChatEventType(int, enum.Enum):
    TEXT_PART = 0                    # 流式文本片段
    DATA_PART = 2                    # 消息元数据（聊天对象、消息对象等）
    ERROR_PART = 3                   # 错误信息
    MESSAGE_ANNOTATIONS_PART = 8     # 消息注解（状态、上下文数据等）
```

### 2. 事件载荷定义

在 `stream_protocol.py` 中定义的 `ChatEvent` 类和相关载荷类型：

```python
# backend/app/rag/chat/stream_protocol.py
@dataclass
class ChatEvent:
    event_type: ChatEventType
    payload: str | ChatStreamPayload | None = None

    def encode(self, charset) -> bytes:
        body = self.payload
        if isinstance(body, ChatStreamPayload):
            body = body.dump()
        body = json.dumps(body, separators=(",", ":"))
        return f"{self.event_type.value}:{body}\n".encode(charset)
```

### 3. 消息状态定义

消息处理的不同阶段在 `types.py` 中定义为 `ChatMessageSate` 枚举：

```python
# backend/app/rag/types.py
class ChatMessageSate(int, enum.Enum):
    TRACE = 0                     # 追踪信息
    SOURCE_NODES = 1              # 源文档节点
    KG_RETRIEVAL = 2              # 知识图谱检索
    REFINE_QUESTION = 3           # 优化问题
    SEARCH_RELATED_DOCUMENTS = 4  # 搜索相关文档
    DATABASE_QUERY = 5            # 数据库查询
    GENERATE_ANSWER = 6           # 生成回答
    TOOL_CALL_PART = 7            # 工具调用
    TOOL_RESULT_PART = 8          # 工具调用结果
    FINISHED = 9                  # 处理完成
```

## 二、事件发送机制

### 1. 聊天流程中的事件发送

在 `chat_flow.py` 中，事件通过 `yield ChatEvent(...)` 方式发送：

```python
# 示例：发送文本片段
yield ChatEvent(
    event_type=ChatEventType.TEXT_PART,
    payload=word,
)

# 示例：发送消息注解
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.KG_RETRIEVAL,
        display="搜索知识图谱获取相关上下文",
    ),
)
```

### 2. 事件发送的关键步骤 - 握手协议

#### 握手开始 - `_chat_start()`

必须在处理开始时调用，创建用户和助手消息并通知前端：

```python
def _chat_start(self) -> Generator[ChatEvent, None, Tuple[DBChatMessage, DBChatMessage]]:
    # 创建用户消息记录
    db_user_message = chat_repo.create_message(...)
    
    # 创建助手消息记录（初始为空内容）
    db_assistant_message = chat_repo.create_message(...)
    
    # 发送数据事件，通知前端已创建消息
    yield ChatEvent(
        event_type=ChatEventType.DATA_PART,
        payload=ChatStreamDataPayload(
            chat=self.db_chat_obj,
            user_message=db_user_message,
            assistant_message=db_assistant_message,
        ),
    )
    
    return db_user_message, db_assistant_message
```

#### 握手结束 - `_chat_finish()`

必须在处理结束时调用，更新助手消息并再次通知前端：

```python
def _chat_finish(self, db_assistant_message, db_user_message, response_text, ...):
    # 更新助手消息
    db_assistant_message.content = response_text
    db_assistant_message.sources = ...
    # ...其他更新

    # 提交到数据库
    self.db_session.add(db_assistant_message)
    self.db_session.commit()
    
    # 发送完成状态
    yield ChatEvent(
        event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
        payload=ChatStreamMessagePayload(state=ChatMessageSate.FINISHED),
    )
    
    # 发送最终数据
    yield ChatEvent(
        event_type=ChatEventType.DATA_PART,
        payload=ChatStreamDataPayload(
            chat=self.db_chat_obj,
            user_message=db_user_message,
            assistant_message=db_assistant_message,
        ),
    )
```

## 三、事件类型详解与使用场景

### 1. TEXT_PART

用于流式传输LLM生成的文本片段。

```python
yield ChatEvent(
    event_type=ChatEventType.TEXT_PART,
    payload="这是一段生成的文本",
)
```

**前端处理**：前端会将这些文本片段追加到当前正在生成的消息中。

### 2. DATA_PART

用于传输聊天和消息的完整元数据，必须在聊天开始和结束时发送。

```python
yield ChatEvent(
    event_type=ChatEventType.DATA_PART,
    payload=ChatStreamDataPayload(
        chat=chat_obj,
        user_message=user_msg,
        assistant_message=assistant_msg,
    ),
)
```

**前端处理**：前端会更新聊天对象和消息对象，包括ID、创建时间、内容等。

### 3. MESSAGE_ANNOTATIONS_PART

用于传输处理状态和中间结果。

```python
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.SEARCH_RELATED_DOCUMENTS,
        display="检索相关知识...",
        context=None,  # 可选上下文数据
        message="",    # 可选消息文本
    ),
)
```

**前端处理**：前端会根据state更新UI显示，展示处理进度和中间结果。

### 4. ERROR_PART

用于传输错误信息。

```python
yield ChatEvent(
    event_type=ChatEventType.ERROR_PART,
    payload="处理过程中发生错误",
)
```

**前端处理**：前端会显示错误信息，终止正在进行的处理。

### 5. 工具相关事件

对于工具调用，可以使用以下事件：

```python
# 工具调用开始
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.TOOL_CALL_PART,
        display=f"调用工具: {tool_name}",
        context={"tool_name": tool_name, "args": args},
    ),
)

# 工具调用结果
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.TOOL_RESULT_PART,
        display=f"工具执行结果",
        context={"tool_name": tool_name, "result": result},
    ),
)
```

## 四、在智能体工作流中实现事件发送

在 `autoflow_agent.py` 中，需要实现一个可靠的事件发送机制：

```python
class BaseAgent:
    def _emit_event(self, event_type: str, payload: Any):
        """发送事件到前端的统一入口"""
        event = None
        
        # 根据事件类型创建相应的ChatEvent
        if event_type == "TEXT_PART":
            event = ChatEvent(
                event_type=ChatEventType.TEXT_PART,
                payload=payload,
            )
        elif event_type == "DATA_PART":
            event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=ChatStreamDataPayload(**payload),
            )
        elif event_type == "MESSAGE_ANNOTATIONS_PART":
            event = ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(**payload),
            )
        elif event_type == "ERROR_PART":
            event = ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=payload,
            )
        
        # 将事件放入事件队列或直接yield出去
        if event:
            self.events.append(event)
```

在实际实现中，各个Agent的方法应该在关键处理步骤中调用`_emit_event`，实现如下特性：

1. 在 `InputProcessorAgent` 中模拟 `_chat_start`
2. 在 `ResponseAgent` 中模拟 `_chat_finish`
3. 各agent的处理过程中发送状态更新

## 五、最佳实践与建议

### 1. 标准化事件发送格式
始终使用 `ChatEvent` 类和相应的载荷类型 (`ChatStreamDataPayload`, `ChatStreamMessagePayload`)。

### 2. 严格遵循握手协议
必须实现 `_chat_start` 和 `_chat_finish` 的功能，确保前端能正确初始化和完成消息处理。

### 3. 明确状态转换
使用 `MESSAGE_ANNOTATIONS_PART` 事件清晰地标记处理阶段的转换，例如从"检索知识"到"生成回答"。

### 4. 适当的粒度
状态更新不宜过于频繁，也不宜过于稀疏。一个好的经验法则是：每个主要处理步骤前后各发送一次状态更新。

### 5. 错误处理
发生错误时，必须发送 `ERROR_PART` 事件，并确保前端能够得到通知。

### 6. 调试友好
为了方便调试，可以在关键事件发送点添加日志记录。