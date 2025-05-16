from typing import Any, Dict, List, Optional, Union
from datetime import datetime

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM
from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.prompts.rich import RichPromptTemplate

from ..context import Context
from ..events import Event, StartEvent, PrepEvent, KnowledgeEvent
from ..workflow import step
from .base_agent import BaseAgent
from app.rag.chat.stream_protocol import ChatEvent, ChatStreamDataPayload
from app.rag.types import ChatEventType
from app.models import ChatMessage as DBChatMessage
from app.repositories import chat_repo

class InputProcessorAgent(BaseAgent):
    """输入处理Agent，负责处理用户输入和问题优化"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None, llm: LLM = None, fast_llm: LLM = None):
        super().__init__(
            name="InputProcessor",
            description="负责处理用户输入和问题优化的Agent",
            db_session=db_session, 
            engine_config=engine_config
        )
        self.llm = llm
        self.fast_llm = fast_llm
        # 数据库聊天对象，从engine_config或上下文中获取
        self.db_chat_obj = None
    
    async def process(self, ctx: Context, event: Event) -> Event:
        """通用处理方法"""
        if isinstance(event, StartEvent):
            # 直接实现处理逻辑，而不是调用另一个方法
            # 获取用户问题和聊天历史
            user_question = event.user_question
            chat_history = event.chat_history
            
            # 记录原始输入到上下文
            await ctx.set("user_question", user_question)
            await ctx.set("chat_history", chat_history)
            
            # 获取数据库聊天对象
            self.db_chat_obj = await ctx.get("db_chat_obj")
            
            # 创建初始消息记录并实现_chat_start握手
            db_user_message, db_assistant_message = await self._chat_start(user_question, chat_history)
            await ctx.set("db_user_message", db_user_message)
            await ctx.set("db_assistant_message", db_assistant_message)
            
            # 判断是否启用了问题优化
            if self.engine_config and getattr(self.engine_config, "refine_question_with_kg", False):
                # 发送状态更新
                self.emit_info("正在优化查询...")
                
                # 执行问题优化
                refined_question = await self._refine_question(user_question, chat_history)
                await ctx.set("refined_question", refined_question)
                
                # 如果问题有明显变化，记录优化结果
                if refined_question.strip() != user_question.strip():
                    self.emit_info(f"优化后的查询: {refined_question}")
            else:
                # 不进行优化，直接使用原始问题
                await ctx.set("refined_question", user_question)
            
            # 继续到下一步
            return PrepEvent()
            
        return PrepEvent()
    
    async def _chat_start(self, user_question: str, chat_history: List[Any]) -> tuple:
        """实现chat_start握手协议，创建用户和助手消息记录
        
        参数:
            user_question: 用户问题
            chat_history: 聊天历史
            
        返回:
            tuple: (用户消息对象, 助手消息对象)
        """
        # 检查是否有db_chat_obj，如果没有则抛出异常
        if not self.db_chat_obj:
            self.logger.error("【chat_start】缺少db_chat_obj，无法创建消息记录")
            raise ValueError("缺少db_chat_obj，无法创建消息记录")
        
        self.logger.info(f"【chat_start】开始创建消息记录: user_question={user_question[:30]}..., db_session存在={self.db_session is not None}")
            
        # 创建用户消息记录
        try:
            self.logger.info("【chat_start】创建用户消息记录")
            db_user_message = chat_repo.create_message(
                session=self.db_session,
                chat=self.db_chat_obj,
                chat_message=DBChatMessage(
                    role=MessageRole.USER.value,  # 设置角色为用户
                    content=user_question.strip(),  # 设置消息内容（去除首尾空格）
                ),
            )
            self.logger.info(f"【chat_start】用户消息创建成功: id={getattr(db_user_message, 'id', 'unknown')}")
        except Exception as e:
            self.logger.error(f"【chat_start】创建用户消息失败: {str(e)}", exc_info=True)
            raise
        
        # 创建助手消息记录（初始为空内容）
        try:
            self.logger.info("【chat_start】创建助手消息记录")
            db_assistant_message = chat_repo.create_message(
                session=self.db_session,
                chat=self.db_chat_obj,
                chat_message=DBChatMessage(
                    role=MessageRole.ASSISTANT.value,  # 设置角色为助手
                    content="",  # 初始内容为空
                ),
            )
            self.logger.info(f"【chat_start】助手消息创建成功: id={getattr(db_assistant_message, 'id', 'unknown')}")
        except Exception as e:
            self.logger.error(f"【chat_start】创建助手消息失败: {str(e)}", exc_info=True)
            raise
        
        # 发送数据事件，通知前端已创建消息
        try:
            self.logger.info("【chat_start】创建并发送ChatEvent通知前端")
            
            # 创建ChatStreamDataPayload
            payload = ChatStreamDataPayload(
                chat=self.db_chat_obj,
                user_message=db_user_message,
                assistant_message=db_assistant_message,
            )
            
            # 直接创建ChatEvent并发送 (使用新的事件系统)
            chat_event = ChatEvent(
                event_type=ChatEventType.DATA_PART,
                payload=payload  # ChatStreamDataPayload的dump方法会返回数组
            )
            
            # 使用emit_event发送事件 (这将触发EventConverter)
            # 注意：这里不再直接操作self.events，而是通过BaseAgent的emit_event发送
            # 这将确保事件通过EventConverter正确转换为前端期望的格式
            # BaseAgent的emit_event方法内部会调用EventConverter.to_chat_event
            # 而EventConverter会将ChatStreamDataPayload正确处理
            
            # 假设_event_emitter已经设置，并且BaseAgent的emit_event会调用它
            # 我们需要确保chat_event对象本身被传递，而不是其序列化形式
            # EventConverter应该负责将BaseEvent转换为ChatEvent，而不是在Agent层面做转换
            
            # 为了适配新的事件系统，我们应该发送一个内部事件，让BaseAgent处理转换
            # 这里我们直接创建一个包含ChatStreamDataPayload的DATA_PART事件
            # 这个逻辑与BaseAgent的emit_event有所不同，需要审视
            
            # 改为使用 emit_event 发送一个自定义的 BaseEvent 或一个通用的事件类型
            # 但这里我们期望发送的是一个已经构建好的ChatEvent的payload
            # 最直接的方式是直接调用 _event_emitter （如果已设置）
            # 或者，让emit_event能够接受一个预构建的ChatEvent
            
            # 修正：InputProcessorAgent不应该直接创建ChatEvent，应该创建内部事件
            # 然后通过self.emit_event发送，BaseAgent会负责转换
            # 但这里的DATA_PART是前端特定的，所以我们用旧的方式发送
            
            # 最终决定：继续使用旧的事件系统，但是确保payload格式正确
            self._emit_legacy_event("DATA_PART", payload.dump()) # 调用dump()确保是数组

            self.logger.info("【chat_start】事件已添加到队列")
        except Exception as e:
            self.logger.error(f"【chat_start】创建或发送事件失败: {str(e)}", exc_info=True)
            raise
        
        self.logger.info("【chat_start】握手完成，返回消息对象")
        return db_user_message, db_assistant_message
    
    async def _refine_question(self, user_question: str, chat_history: List[Any]) -> str:
        """优化用户问题，使其更清晰、更容易检索"""
        # 优先使用fast_llm进行问题优化
        decision_llm = self.fast_llm or self.llm
        if not decision_llm:
            return user_question
            
        try:
            # 使用默认的问题优化提示词
            from app.rag.chat.config import LLMOption
            prompt_template = RichPromptTemplate(template_str=LLMOption().condense_question_prompt)
            
            # 准备提示词模板的输入
            # 转换chat_history为llama_index期望的格式
            formatted_history = []
            for msg in chat_history:
                if isinstance(msg, dict):
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    formatted_history.append(f"{'H' if role == 'user' else 'Assistant'}: {content}")
            
            # 使用模板预测，使用fast_llm
            refined_question = decision_llm.predict(
                prompt_template,
                graph_knowledges="",  # 这里暂时为空，因为还没有知识图谱结果
                chat_history="\n".join(formatted_history),
                question=user_question,
                current_date=datetime.now().strftime("%Y-%m-%d")
            )
            
            return refined_question.strip() if refined_question else user_question
            
        except Exception as e:
            # 如果优化过程中出错，返回原始问题
            print(f"问题优化出错: {str(e)}")
            return user_question 