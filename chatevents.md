
以下是chat_flow.py中所有使用ChatEvent的实例，按事件类型分类：

### 错误事件
```python
# 处理异常时发送错误事件
yield ChatEvent(
    event_type=ChatEventType.ERROR_PART,
    payload="处理聊天时遇到错误。请稍后再试。",
)
```

### 数据事件
```python
# 创建消息后发送数据事件
yield ChatEvent(
    event_type=ChatEventType.DATA_PART,
    payload=ChatStreamDataPayload(
        chat=self.db_chat_obj,
        user_message=db_user_message,
        assistant_message=db_assistant_message,
    ),
)

# 聊天完成时发送数据事件
yield ChatEvent(
    event_type=ChatEventType.DATA_PART,
    payload=ChatStreamDataPayload(
        chat=self.db_chat_obj,
        user_message=db_user_message,
        assistant_message=db_assistant_message,
    ),
)
```

### 消息注释事件
```python
# 知识图谱检索状态
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.KG_RETRIEVAL,
        display="识别问题意图并执行知识图谱搜索",
    ),
)

yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.KG_RETRIEVAL,
        display="搜索知识图谱获取相关上下文",
    ),
)

# 问题重写状态
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.REFINE_QUESTION,
        display="查询重写以增强信息检索",
    ),
)

yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.REFINE_QUESTION,
        message=refined_question,
    ),
)

# 文档搜索状态
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.SEARCH_RELATED_DOCUMENTS,
        display="检索最相关的文档",
    ),
)

# 源文档展示
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.SOURCE_NODES,
        context=source_documents,
    ),
)

# 生成答案状态
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.GENERATE_ANSWER,
        display="使用大模型生成精确答案",
    ),
)

# 完成状态
yield ChatEvent(
    event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
    payload=ChatStreamMessagePayload(
        state=ChatMessageSate.FINISHED,
    ),
)
```

### 文本事件
```python
# 需要澄清时发送文本事件
yield ChatEvent(
    event_type=ChatEventType.TEXT_PART,
    payload=need_clarify_response,
)

# 流式输出回答时发送文本事件
yield ChatEvent(
    event_type=ChatEventType.TEXT_PART,
    payload=word,
)

# 从缓存返回回答时发送文本事件
yield ChatEvent(
    event_type=ChatEventType.TEXT_PART,
    payload=chunk,
)
```

这些是文件中所有使用ChatEvent的地方，事件类型包括：
- `ChatEventType.ERROR_PART`：错误信息
- `ChatEventType.DATA_PART`：聊天数据更新
- `ChatEventType.MESSAGE_ANNOTATIONS_PART`：消息状态和注释
- `ChatEventType.TEXT_PART`：文本内容
