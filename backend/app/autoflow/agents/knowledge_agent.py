import asyncio
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex
from llama_index.core.prompts.rich import RichPromptTemplate
from llama_index.core.schema import NodeWithScore

from ..context import Context
from ..events import Event, StartEvent, PrepEvent, KnowledgeEvent, ReasoningEvent, ResponseEvent
from ..workflow import step
from .base_agent import BaseAgent
from ..retrievers import KnowledgeRetriever

# 添加专用日志器
logger = logging.getLogger("autoflow.agents")

class KnowledgeAgent(BaseAgent):
    """知识Agent，负责检索知识和澄清问题"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None, llm: LLM = None, fast_llm: LLM = None):
        super().__init__(db_session, engine_config)
        self.llm = llm
        self.fast_llm = fast_llm
        self.knowledge_index = None  # 向量存储索引
        self.kg_index = None  # 知识图谱索引
        
        # 创建知识检索工具实例
        logger.info("【KnowledgeAgent】初始化知识检索工具")
        self.retriever = KnowledgeRetriever(
            db_session=db_session,
            engine_config=engine_config,
            llm=llm,
            fast_llm=fast_llm
        )
        logger.info(f"【KnowledgeAgent】初始化完成, engine_config={engine_config is not None}, llm={llm is not None}, fast_llm={fast_llm is not None}")
    
    def set_indices(self, knowledge_index, kg_index=None):
        """设置索引实例"""
        logger.info(f"【KnowledgeAgent】设置索引: knowledge_index={knowledge_index is not None}, kg_index={kg_index is not None}")
        self.knowledge_index = knowledge_index
        self.kg_index = kg_index
        
        # 同时更新检索工具的索引
        self.retriever.vector_index = knowledge_index
        self.retriever.kg_index = kg_index
        logger.info("【KnowledgeAgent】索引设置完成")
    
    @step
    async def process(self, ctx: Context, event: Event) -> Event:
        """通用处理方法"""
        logger.info(f"【KnowledgeAgent】开始处理事件: {type(event).__name__}")
        
        if isinstance(event, PrepEvent):
            logger.info("【KnowledgeAgent】处理PrepEvent，开始检索知识")
            # 获取基本信息
            user_question = await ctx.get("user_question", "")
            refined_question = await ctx.get("refined_question", "")
            if not refined_question:
                refined_question = user_question
                logger.info(f"【KnowledgeAgent】使用原始问题: {user_question[:50]}...")
            else:
                logger.info(f"【KnowledgeAgent】使用优化问题: {refined_question[:50]}...")
                
            chat_history = await ctx.get("chat_history", [])
            logger.info(f"【KnowledgeAgent】聊天历史长度: {len(chat_history)}")
            
            # 解析并存储上下文
            knowledge_graph_context = ""
            retrieved_nodes = []
            
            # 通知前端开始知识检索
            logger.info("【KnowledgeAgent】发送前端通知: 开始知识检索")
            self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                "state": "KNOWLEDGE_RETRIEVAL",
                "display": "检索相关知识..."
            })
            
            # 步骤1: 先查询知识图谱(如果有)
            if self.kg_index:
                logger.info("【KnowledgeAgent】开始查询知识图谱")
                self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                    "state": "KG_QUERY",
                    "display": "查询知识图谱..."
                })
                
                # 使用retriever查询知识图谱
                try:
                    logger.info(f"【KnowledgeAgent】调用search_knowledge_graph, 问题: {refined_question[:50]}...")
                    knowledge_graph_context = await self.retriever.search_knowledge_graph(refined_question)
                    logger.info(f"【KnowledgeAgent】知识图谱检索完成，结果长度: {len(knowledge_graph_context)}")
                    await ctx.set("knowledge_graph_context", knowledge_graph_context)
                    
                    # 如果有知识图谱结果，发送注释
                    if knowledge_graph_context:
                        logger.info("【KnowledgeAgent】发送前端通知: 知识图谱查询结果")
                        self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                            "state": "KG_RESULT",
                            "display": "从知识图谱找到相关信息"
                        })
                except Exception as e:
                    logger.error(f"【KnowledgeAgent错误】知识图谱查询出错: {str(e)}", exc_info=True)
            else:
                logger.info("【KnowledgeAgent】没有配置知识图谱索引，跳过知识图谱查询")
            
            # 步骤2: 检查是否需要澄清问题，使用fast_llm进行决策
            if getattr(self.engine_config, "clarify_question", False) and self.fast_llm:
                logger.info("【KnowledgeAgent】检查是否需要澄清问题")
                try:
                    needs_clarification, clarification_message = await self.retriever.check_clarification_needed(
                        refined_question, 
                        knowledge_graph_context
                    )
                    
                    logger.info(f"【KnowledgeAgent】问题澄清检查结果: needs_clarification={needs_clarification}")
                    
                    # 如果需要澄清，发送注释
                    if needs_clarification:
                        logger.info(f"【KnowledgeAgent】需要澄清问题: {clarification_message[:100]}...")
                        self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                            "state": "CLARIFICATION_NEEDED",
                            "display": clarification_message
                        })
                        
                        # 这里我们不暂停执行，而是直接继续执行下一步
                        # 实际应用中，可能需要等待用户进一步输入
                except Exception as e:
                    logger.error(f"【KnowledgeAgent错误】问题澄清检查出错: {str(e)}", exc_info=True)
            
            # 步骤3: 检索向量库
            if self.knowledge_index:
                logger.info("【KnowledgeAgent】开始检索向量库")
                self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                    "state": "VECTOR_SEARCH",
                    "display": "搜索知识库..."
                })
                
                # 使用retriever查询向量库
                try:
                    logger.info(f"【KnowledgeAgent】调用search_vector_store, 问题: {refined_question[:50]}...")
                    retrieved_nodes = await self.retriever.search_vector_store(refined_question)
                    logger.info(f"【KnowledgeAgent】向量检索完成，结果数量: {len(retrieved_nodes)}")
                    await ctx.set("knowledge_nodes", retrieved_nodes)
                    
                    # 发送检索结果信息
                    self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                        "state": "KNOWLEDGE_RETRIEVED",
                        "display": f"找到 {len(retrieved_nodes)} 条相关知识"
                    })
                    
                    # 发送头部知识源预览
                    if retrieved_nodes:
                        preview_nodes = retrieved_nodes[:2]  # 只预览前2个结果
                        preview_text = "\n\n".join([
                            f"- {self._get_source_title(node)}: {node.get('text', '')[:100]}..."
                            for node in preview_nodes
                        ])
                        
                        logger.info(f"【KnowledgeAgent】发送知识预览: {preview_text[:200]}...")
                        self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                            "state": "KNOWLEDGE_PREVIEW",
                            "display": f"知识预览:\n{preview_text}"
                        })
                except Exception as e:
                    logger.error(f"【KnowledgeAgent错误】向量检索出错: {str(e)}", exc_info=True)
                    # 错误情况下，确保仍然继续流程
                    self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                        "state": "KNOWLEDGE_RETRIEVED",
                        "display": "未找到相关知识"
                    })
            else:
                logger.info("【KnowledgeAgent】没有配置向量索引，跳过向量检索")
                
                # 没有向量索引的情况下，通知前端
                self._emit_event("MESSAGE_ANNOTATIONS_PART", {
                    "state": "KNOWLEDGE_RETRIEVED",
                    "display": "系统未配置知识库"
                })
            
            # 返回下一个事件
            logger.info(f"【KnowledgeAgent】知识检索完成，返回KnowledgeEvent事件, retrieved_nodes={len(retrieved_nodes)}, knowledge_graph_context长度={len(knowledge_graph_context)}")
            return KnowledgeEvent(
                knowledge_nodes=retrieved_nodes,
                knowledge_graph_context=knowledge_graph_context
            )
        
        logger.warning(f"【KnowledgeAgent】未处理的事件类型: {type(event).__name__}，返回空KnowledgeEvent")
        return KnowledgeEvent(knowledge_nodes=[], knowledge_graph_context="")
    
    def _get_source_title(self, node: Dict) -> str:
        """从节点中提取源标题"""
        if not node or not isinstance(node, dict):
            return "Unknown"
            
        metadata = node.get("metadata", {})
        if metadata:
            # 按优先级尝试不同的元数据字段
            for field in ["title", "source", "file_name", "file_path"]:
                if field in metadata and metadata[field]:
                    return str(metadata[field])
                    
        return "Unknown Source"
    
    async def _run_async(self, func, *args, **kwargs):
        """将同步函数异步运行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 