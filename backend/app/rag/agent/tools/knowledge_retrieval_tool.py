"""
知识检索工具模块

提供从知识库中检索相关文档的工具
"""

import logging
from typing import Dict, List, Optional, Any

from llama_index.core.schema import NodeWithScore
from llama_index.core.tools.types import BaseTool, ToolMetadata
from sqlmodel import Session

from app.rag.chat.retrieve.retrieve_flow import RetrieveFlow
from app.models import KnowledgeBase
from app.rag.chat.config import ChatEngineConfig

logger = logging.getLogger(__name__)

class KnowledgeRetrievalTool(BaseTool):
    """
    知识检索工具
    
    从知识库中检索与查询相关的文档片段
    """
    
    def __init__(
        self,
        db_session: Session,
        engine_config: ChatEngineConfig,
        description: str = "从知识库中检索与用户问题相关的内容",
    ):
        """
        初始化知识检索工具
        
        参数:
            db_session: 数据库会话对象
            engine_config: 聊天引擎配置
            description: 工具描述
        """
        self.db_session = db_session
        self.engine_config = engine_config
        self.knowledge_bases = self.engine_config.get_knowledge_bases(db_session)
        
        # 初始化检索流程
        self.retrieve_flow = RetrieveFlow(
            db_session=self.db_session,
            engine_name=engine_config._db_chat_engine.name if engine_config._db_chat_engine else "default",
            engine_config=self.engine_config,
            llm=engine_config.get_llama_llm(db_session),
            fast_llm=engine_config.get_fast_llama_llm(db_session),
            knowledge_bases=self.knowledge_bases,
        )
        
        # 创建ToolMetadata对象并直接设置到self._metadata
        self._metadata = ToolMetadata(name="knowledge_retrieval", description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        """返回工具的元数据信息"""
        return self._metadata
    
    def _node_to_dict(self, node: NodeWithScore) -> Dict:
        """
        将NodeWithScore转换为前端友好的字典格式
        
        参数:
            node: 带分数的节点对象
            
        返回:
            Dict: 包含节点信息的字典
        """
        return {
            "text": node.node.text,
            "score": float(node.score),  # 确保score是普通浮点数而非numpy类型
            "metadata": node.node.metadata,
            "id": node.node.id_
        }
    
    def __call__(self, query_str: str, top_k: int = 5) -> Dict:
        """
        根据查询检索相关文档
        
        参数:
            query_str: 用户查询文本
            top_k: 返回的最大结果数
            
        返回:
            Dict: 包含检索结果和元数据的字典
        """
        logger.info(f"执行知识检索: {query_str}")
        try:
            # 执行检索
            rerank = False
            if hasattr(self.engine_config.vector_search, 'reranker') and self.engine_config.vector_search.reranker:
                rerank = self.engine_config.vector_search.reranker.enabled
            
            retrieval_results = self.retrieve_flow.retrieve(
                query_str=query_str,
                top_k=top_k,
                rerank=rerank,
            )
            
            # 转换结果为前端友好格式
            result = {
                "nodes": [self._node_to_dict(node) for node in retrieval_results],
                "count": len(retrieval_results),
                "knowledge_bases": [kb.name for kb in self.knowledge_bases],
                "success": True
            }
            return result
        except Exception as e:
            logger.error(f"知识检索失败: {str(e)}")
            return {
                "nodes": [],
                "count": 0,
                "error": str(e),
                "success": False
            } 