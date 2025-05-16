from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM
from llama_index.core.prompts.rich import RichPromptTemplate

from ..context import Context
from ..events import Event, ResponseEvent, StopEvent
from ..workflow import step
from .base_agent import BaseAgent
from app.rag.chat.stream_protocol import ChatEvent, ChatStreamDataPayload, ChatStreamMessagePayload
from app.rag.types import ChatEventType, ChatMessageSate
from app.repositories import chat_repo

class ResponseAgent(BaseAgent):
    """响应Agent，负责生成最终回答并处理回调"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None, llm: LLM = None, fast_llm: LLM = None):
        super().__init__(
            name="ResponseAgent",
            description="负责生成最终回答并处理回调的智能体",
            db_session=db_session, 
            engine_config=engine_config
        )
        self.llm = llm
        self.fast_llm = fast_llm  # 添加fast_llm但不使用，因为ResponseAgent主要生成长文本答案
        self.callback = None
        # 数据库聊天对象，从上下文中获取
        self.db_chat_obj = None
    
    def set_callback(self, callback):
        """设置回调函数"""
        self.callback = callback
    
    async def process(self, ctx: Context, event: Event) -> Event:
        """通用处理方法"""
        if isinstance(event, ResponseEvent):
            # 获取基本信息
            refined_question = await ctx.get("refined_question", "")
            if not refined_question:
                refined_question = await ctx.get("user_question", "")
                
            knowledge_nodes = await ctx.get("knowledge_nodes", [])
            knowledge_graph_context = await ctx.get("knowledge_graph_context", "")
            reasoning_result = await ctx.get("reasoning_result", "")
            
            # 获取数据库聊天对象
            self.db_chat_obj = await ctx.get("db_chat_obj")
            
            # 通知前端开始生成回答
            self.emit_info("生成最终回答...")
            
            # 生成最终回答
            answer = await self._generate_answer(
                question=refined_question,
                knowledge_nodes=knowledge_nodes,
                knowledge_graph_context=knowledge_graph_context,
                reasoning_result=reasoning_result
            )
            
            # 更新数据库中的助手消息
            db_user_message = await ctx.get("db_user_message")
            db_assistant_message = await ctx.get("db_assistant_message")
            
            # 发送最终文本
            self.emit_text(answer)
            
            # 执行_chat_finish握手
            await self._chat_finish(
                db_assistant_message=db_assistant_message, 
                db_user_message=db_user_message,
                response_text=answer,
                knowledge_nodes=knowledge_nodes
            )
            
            # 执行回调
            if self.callback:
                await self._run_callback(ctx)
            
            # 返回停止事件，结束工作流
            return StopEvent(result=answer)
        
        return StopEvent(result="未处理的事件类型")
    
    async def _generate_answer(self, question: str, knowledge_nodes: List[Dict], knowledge_graph_context: str, reasoning_result: str) -> str:
        """生成最终回答"""
        if not self.llm:
            return "无法生成回答：LLM未配置"
            
        try:
            # 使用默认的答案生成提示词
            from app.rag.chat.config import LLMOption
            prompt_template = RichPromptTemplate(template_str=LLMOption().text_qa_prompt)
            
            # 准备上下文内容
            context_str = self._format_knowledge_nodes_as_text(knowledge_nodes)
            
            # 使用模板预测
            answer = self.llm.predict(
                prompt_template,
                graph_knowledges=knowledge_graph_context or "",
                context_str=context_str,
                database_results="",  # 这里假设没有数据库结果
                original_question=question,
                query_str=question,
                current_date=datetime.now().strftime("%Y-%m-%d")
            )
            
            return answer.strip()
            
        except Exception as e:
            # 如果生成过程中出错，返回错误信息
            print(f"回答生成出错: {str(e)}")
            return f"生成回答过程中出现错误: {str(e)}"
    
    def _format_knowledge_nodes_as_text(self, nodes: List[Dict]) -> str:
        """将知识节点格式化为文本"""
        if not nodes:
            return "No relevant information found."
            
        texts = []
        for i, node in enumerate(nodes):
            text = node.get("text", "")
            source = ""
            metadata = node.get("metadata", {})
            if metadata:
                title = metadata.get("title", "")
                file_name = metadata.get("file_name", "")
                source = title or file_name or "Unknown Source"
                
            texts.append(f"[{i+1}] Source: {source}\n{text}\n")
            
        return "\n".join(texts)
    
    async def _chat_finish(self, db_assistant_message: Dict, db_user_message: Dict, response_text: str, knowledge_nodes: List[Dict] = None):
        """实现_chat_finish握手协议，完成聊天处理
        
        参数:
            db_assistant_message: 助手消息对象
            db_user_message: 用户消息对象
            response_text: 回答文本
            knowledge_nodes: 知识节点列表
        """
        # 检查是否有db_chat_obj
        if not self.db_chat_obj:
            raise ValueError("缺少db_chat_obj，无法完成聊天")
            
        try:
            # 获取当前时间
            now = datetime.now()
            
            # 使用ChatEvent发送完成状态
            chat_event = ChatEvent(
                event_type=ChatEventType.MESSAGE_ANNOTATIONS_PART,
                payload=ChatStreamMessagePayload(
                    state=ChatMessageSate.FINISHED,
                ),
            )
            self.events.append(chat_event)
            
            # 准备源文档
            sources = []
            if knowledge_nodes:
                for node in knowledge_nodes:
                    source = {
                        "text": node.get("text", ""),
                        "score": node.get("score", 1.0),
                        "metadata": {}
                    }
                    
                    metadata = node.get("metadata", {})
                    if metadata:
                        for key in ["title", "source", "file_name", "file_path", "page_number", "chunk_id"]:
                            if key in metadata:
                                source["metadata"][key] = metadata[key]
                    
                    sources.append(source)
            
            # 更新助手消息
            db_assistant_message.content = response_text
            if hasattr(db_assistant_message, 'sources'):
                db_assistant_message.sources = sources
            if hasattr(db_assistant_message, 'updated_at'):
                db_assistant_message.updated_at = now
            if hasattr(db_assistant_message, 'finished_at'):
                db_assistant_message.finished_at = now
            
            # 更新用户消息
            if hasattr(db_user_message, 'updated_at'):
                db_user_message.updated_at = now
            if hasattr(db_user_message, 'finished_at'):
                db_user_message.finished_at = now
            
            # 提交变更到数据库
            chat_repo.update_message(self.db_session, db_assistant_message)
            chat_repo.update_message(self.db_session, db_user_message)
            
            # 发送最终数据事件
            final_event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=ChatStreamDataPayload(
                    chat=self.db_chat_obj,
                    user_message=db_user_message,
                    assistant_message=db_assistant_message,
                ),
            )
            self.events.append(final_event)
            
        except Exception as e:
            # 如果处理失败，发送错误事件
            error_event = ChatEvent(
                event_type=ChatEventType.ERROR_PART,
                payload=f"完成聊天处理失败: {str(e)}"
            )
            self.events.append(error_event)
            print(f"完成聊天处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
    async def _run_callback(self, ctx: Context):
        """执行回调函数"""
        try:
            # 提取回调所需的参数
            user_message = await ctx.get("db_user_message")
            assistant_message = await ctx.get("db_assistant_message")
            
            # 添加其他可能需要的参数
            knowledge_nodes = await ctx.get("knowledge_nodes", [])
            
            # 执行回调
            if self.callback:
                await self.callback(
                    user_message=user_message,
                    assistant_message=assistant_message,
                    knowledge_nodes=knowledge_nodes
                )
        except Exception as e:
            # 记录回调执行错误
            print(f"回调执行错误: {str(e)}") 