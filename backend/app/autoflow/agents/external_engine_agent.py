from typing import Any, Dict, List, Optional, Union
import json
import logging
import requests
from datetime import datetime

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM

from ..context import Context
from ..events import Event, ExternalEngineEvent, StopEvent
from .base_agent import BaseAgent
from app.rag.chat.stream_protocol import ChatEvent
from app.rag.types import ChatEventType

logger = logging.getLogger(__name__)

class ExternalEngineAgent(BaseAgent):
    """外部引擎代理，负责调用外部引擎处理查询"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None, llm: LLM = None, fast_llm: LLM = None):
        super().__init__(db_session, engine_config)
        self.llm = llm
        self.fast_llm = fast_llm
        # 从engine_config获取外部引擎配置
        self.external_engine_config = None
        if engine_config and hasattr(engine_config, "external_engine_config"):
            self.external_engine_config = engine_config.external_engine_config
    
    async def process(self, ctx: Context, event: Event) -> Event:
        """外部引擎处理方法"""
        if isinstance(event, ExternalEngineEvent):
            # 获取基本信息
            goal = event.goal
            response_format = event.response_format
            
            # 获取用户和助手消息
            db_user_message = await ctx.get("db_user_message")
            db_assistant_message = await ctx.get("db_assistant_message")
            self.db_chat_obj = await ctx.get("db_chat_obj")
            
            # 调用外部引擎
            await self._call_external_engine(
                goal=goal,
                response_format=response_format,
                db_user_message=db_user_message, 
                db_assistant_message=db_assistant_message
            )
            
            # 返回停止事件，结束工作流
            return StopEvent(result="已使用外部引擎处理")
            
        # 如果不是ExternalEngineEvent，返回原始事件
        return event
    
    async def _call_external_engine(self, goal: str, response_format: dict, db_user_message: Any, db_assistant_message: Any):
        """调用外部引擎处理查询"""
        if not self.external_engine_config:
            self._emit_event("ERROR_PART", "未配置外部引擎")
            return
            
        # 获取外部引擎API地址
        stream_chat_api_url = self.external_engine_config.stream_chat_api_url
        if not stream_chat_api_url:
            self._emit_event("ERROR_PART", "未配置外部引擎API地址")
            return
            
        try:
            # 准备聊天参数
            chat_params = {
                "goal": goal,
                "response_format": response_format,
                "namespace_name": "Default",
            }
            
            # 发送状态更新
            self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                "state": "EXTERNAL_ENGINE_CALL",
                "display": "调用外部引擎处理..."
            })
            
            # 发送请求并处理流式响应
            logger.info(f"请求外部引擎API: {stream_chat_api_url}")
            res = requests.post(stream_chat_api_url, json=chat_params, stream=True)
            
            # 解析响应
            response_text = ""
            task_id = None
            
            # 处理流式响应
            for line in res.iter_lines():
                if not line:
                    continue
                    
                chunk = line.decode("utf-8")
                # 处理文本片段 (0:表示文本片段)
                if chunk.startswith("0:"):
                    word = json.loads(chunk[2:])
                    response_text += word
                    self._emit_event("TEXT_PART", word)
                # 处理状态信息 (8:表示状态信息)
                elif chunk.startswith("8:"):
                    try:
                        states = json.loads(chunk[2:])
                        if len(states) > 0:
                            task_id = states[0].get("task_id")
                    except Exception as e:
                        logger.error(f"解析状态信息出错: {e}")
                # 其他类型的消息直接转发
                else:
                    self._emit_event("TEXT_PART", chunk)
            
            # 更新消息
            now = datetime.now()
            
            # 构建基础URL和追踪URL
            base_url = stream_chat_api_url.replace("/api/stream_execute_vm", "")
            trace_url = f"{base_url}?task_id={task_id}" if task_id else ""
            
            # 更新助手消息
            if db_assistant_message:
                db_assistant_message["content"] = response_text
                db_assistant_message["trace_url"] = trace_url
                db_assistant_message["meta"] = {
                    "task_id": task_id,
                    "goal": goal,
                    **response_format,
                }
                db_assistant_message["updated_at"] = now.isoformat()
                db_assistant_message["finished_at"] = now.isoformat()
            
            # 更新用户消息
            if db_user_message:
                db_user_message["trace_url"] = trace_url
                db_user_message["meta"] = {
                    "task_id": task_id,
                    "goal": goal,
                    **response_format,
                }
                db_user_message["updated_at"] = now.isoformat()
                db_user_message["finished_at"] = now.isoformat()
            
            # 发送完成状态
            self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                "state": "FINISHED"
            })
            
            # 发送最终数据
            self._emit_event("DATA_PART", {
                "chat": self.db_chat_obj,
                "user_message": db_user_message,
                "assistant_message": db_assistant_message
            })
            
        except Exception as e:
            # 处理错误
            error_msg = f"调用外部引擎出错: {str(e)}"
            logger.error(error_msg)
            self._emit_event("ERROR_PART", error_msg) 