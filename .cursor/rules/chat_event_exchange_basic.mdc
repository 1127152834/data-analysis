---
description: 
globs: 
alwaysApply: false
---

我将通过查看前端代码，结合 chat_event_basic_front.mdc 文档，来分析前端实际支持的事件类型和处理逻辑。

Ran tool
让我先检查前端的状态定义和事件处理机制：

Read file: frontend/app/src/components/chat/chat-stream-state.ts

Read file: frontend/app/src/components/chat/chat-controller.ts

Read file: frontend/app/src/components/chat/chat-controller.ts

Read file: frontend/app/src/components/chat/chat-message-controller.ts

Read file: frontend/app/src/components/chat/message-annotation-history.tsx

Read file: frontend/app/src/components/chat/message-annotation-tool-events.tsx

Read file: frontend/app/src/components/chat/message-annotation-history-stackvm.tsx
基于对前端代码和chat_event_basic_front.mdc文档的分析，我现在可以给出更准确的前后端事件通信支持清单。

# 前后端事件通信支持清单

## 1. 前端支持的事件类型

前端确实支持以下事件类型，这些都是在`chat-controller.ts`中的`_processPart`方法中处理的：

1. **文本流传输 (TEXT_PART → "text")**
   - 用途：流式传输生成的文本内容
   - 处理方法：`_processTextPart()`

2. **消息元数据 (DATA_PART → "data")**
   - 用途：实现握手协议，创建和更新消息
   - 处理方法：`_processDataPart()`

3. **错误信息 (ERROR_PART → "error")**
   - 用途：显示错误信息，如LLM调用失败
   - 处理方法：`_processErrorPart()`

4. **状态注解 (MESSAGE_ANNOTATIONS_PART → "message_annotations")**
   - 用途：更新处理状态，显示处理过程
   - 处理方法：`_processMessageAnnotationPart()`

5. **工具调用 (tool_call)**
   - 用途：处理工具调用
   - 处理方法：`_processToolCallPart()`

6. **工具结果 (tool_result)**
   - 用途：处理工具调用结果
   - 处理方法：`_processToolResultPart()`

## 2. 前端支持的消息状态 (AppChatStreamState)

根据`chat-stream-state.ts`代码，前端真实支持以下状态：

```typescript
export const enum AppChatStreamState {
  CONNECTING = 'CONNECTING', // 仅前端状态
  TRACE = 'TRACE',
  SOURCE_NODES = 'SOURCE_NODES',
  KG_RETRIEVAL = 'KG_RETRIEVAL',
  REFINE_QUESTION = 'REFINE_QUESTION',
  SEARCH_RELATED_DOCUMENTS = 'SEARCH_RELATED_DOCUMENTS',
  RERANKING = 'RERANKING',  // 重排序状态
  GENERATE_ANSWER = 'GENERATE_ANSWER',
  FINISHED = 'FINISHED',
  FAILED = 'FAILED',  // 失败状态
  UNKNOWN = 'UNKNOWN', // 仅前端状态
  TOOL_CALL = 'TOOL_CALL',  // 工具调用
  TOOL_RESULT = 'TOOL_RESULT',  // 工具调用结果
}
```

文档中提到的`AGENT_THINKING_PART`在当前前端代码中确实不存在。

## 3. 握手协议实现

前端通过`ChatController`的`_processDataPart`方法实现握手：

```typescript
private _processDataPart (ongoingMessageController, part) {
  const { chat, user_message, assistant_message } = chatDataPartSchema.parse(fixChatInitialData(part.value[0]));
  this.updateChat(chat);
  this.upsertMessage(user_message);
  
  if (!ongoingMessageController) {
    // 聊天开始：创建助手消息控制器
    ongoingMessageController = this.createMessage(assistant_message, true);
    this._postInitialized = true;
    this.emit('post-initialized');
  } else {
    // 聊天结束：更新助手消息
    ongoingMessageController.update(assistant_message);
  }
  
  return ongoingMessageController;
}
```

## 4. 可视化状态历史

前端使用`MessageAnnotationHistory`组件显示消息处理的状态历史，包括已完成的状态和当前正在进行的状态。每个状态显示:
- 状态名称
- 时间戳
- 可能的附加信息

## 5. 工具调用支持

前端支持工具调用的显示，通过`StackVMMessageAnnotationHistory`组件可以更详细地展示工具调用信息：
- 工具名称
- 参数
- 调用结果

## 6. 错误处理

前端能够显示错误信息，使用`MessageAnnotationHistoryError`组件。

## 后端实现建议

基于前端的实际支持，后端应该：

1. **确保状态枚举一致性**：
   ```python
   # 在app/rag/types.py中确保ChatMessageSate包含前端需要的所有状态
   class ChatMessageSate(Enum):
       TRACE = "TRACE"
       SOURCE_NODES = "SOURCE_NODES"
       KG_RETRIEVAL = "KG_RETRIEVAL"
       REFINE_QUESTION = "REFINE_QUESTION"
       SEARCH_RELATED_DOCUMENTS = "SEARCH_RELATED_DOCUMENTS"
       RERANKING = "RERANKING"  # 新增
       GENERATE_ANSWER = "GENERATE_ANSWER"
       FINISHED = "FINISHED"
       FAILED = "FAILED"  # 新增
       TOOL_CALL = "TOOL_CALL"
       TOOL_RESULT = "TOOL_RESULT"
   ```

2. **实现握手协议**：
   在InputProcessorAgent中实现`_chat_start`:
   ```python
   async def _chat_start(self, user_question: str, chat_history: List[Any]) -> tuple:
       # 创建用户和助手消息记录
       db_user_message = chat_repo.create_message(...)
       db_assistant_message = chat_repo.create_message(...)
       
       # 发送DATA_PART事件
       chat_event = ChatEvent(
           event_type=ChatEventType.DATA_PART,
           payload=ChatStreamDataPayload(
               chat=self.db_chat_obj,
               user_message=db_user_message,
               assistant_message=db_assistant_message,
           ),
       )
       self.events.append(chat_event)
       
       return db_user_message, db_assistant_message
   ```

   在ResponseAgent中实现`_chat_finish`:
   ```python
   async def _chat_finish(self, db_assistant_message, db_user_message, response_text, knowledge_nodes):
       # 更新消息内容
       db_assistant_message.content = response_text
       
       # 发送完成状态
       chat_event = ChatEvent(
           event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
           payload=ChatStreamMessagePayload(
               state=ChatMessageSate.FINISHED,
           ),
       )
       self.events.append(chat_event)
       
       # 发送DATA_PART事件
       final_event = ChatEvent(
           event_type=ChatEventType.DATA_PART,
           payload=ChatStreamDataPayload(
               chat=self.db_chat_obj,
               user_message=db_user_message,
               assistant_message=db_assistant_message,
           ),
       )
       self.events.append(final_event)
   ```

3. **发送状态更新**：
   ```python
   # 例如在KnowledgeAgent中
   self._emit_event("MESSAGE_ANNOTATIONS_PART", {
       "state": "SEARCH_RELATED_DOCUMENTS",
       "display": "正在搜索相关文档..."
   })
   
   # 发送知识节点
   self._emit_event("MESSAGE_ANNOTATIONS_PART", {
       "state": "SOURCE_NODES",
       "context": knowledge_nodes  # 知识节点列表
   })
   ```

4. **工具调用支持**：
   ```python
   # 发送工具调用
   self._emit_event("TOOL_CALL", {
       "toolCallId": tool_call_id,
       "toolName": tool_name,
       "args": tool_args
   })
   
   # 发送工具结果
   self._emit_event("TOOL_RESULT", {
       "toolCallId": tool_call_id,
       "result": tool_result
   })
   ```