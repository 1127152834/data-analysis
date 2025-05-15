"""
知识图谱查询工具模块

提供从知识图谱中检索实体关系的工具
"""

import logging
from typing import Dict, List, Optional, Any

from llama_index.core.tools.types import BaseTool, ToolMetadata, ToolOutput
from sqlmodel import Session

from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetriever, KnowledgeGraphRetrievalResult
from app.rag.chat.config import ChatEngineConfig

logger = logging.getLogger(__name__)

class KnowledgeGraphQueryTool(BaseTool):
    """
    知识图谱查询工具
    
    从知识图谱中检索与查询相关的实体和关系
    """
    
    def __init__(
        self,
        db_session: Session,
        engine_config: ChatEngineConfig,
        description: str = "从知识图谱中查询与用户问题相关的实体和关系",
    ):
        """
        初始化知识图谱查询工具
        
        参数:
            db_session: 数据库会话对象
            engine_config: 聊天引擎配置
            description: 工具描述
        """
        self.db_session = db_session
        self.engine_config = engine_config
        
        # 初始化知识图谱检索器
        from app.rag.chat.kg_retriever import DatabaseMetadataKGRetriever
        # TODO: 实现适当的知识图谱检索器适配
        # self.kg_retriever = KnowledgeGraphRetriever实现类
        
        # 直接设置元数据
        self._metadata = ToolMetadata(name="knowledge_graph_query", description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        """返回工具的元数据信息"""
        return self._metadata
    
    def _format_kg_result(self, kg_result: KnowledgeGraphRetrievalResult) -> Dict:
        """
        格式化知识图谱检索结果为前端友好的格式
        
        参数:
            kg_result: 知识图谱检索结果
            
        返回:
            Dict: 格式化后的结果
        """
        # 提取并格式化三元组
        formatted_triples = []
        for triple in kg_result.relationships:
            formatted_triples.append({
                "subject": triple.source_entity_id,
                "predicate": triple.description,
                "object": triple.target_entity_id,
                "score": float(triple.weight) if triple.weight is not None else None,
            })
        
        # 返回结构化结果
        return {
            "triples": formatted_triples,
            "count": len(formatted_triples),
            "entities": [e.model_dump() for e in kg_result.entities],
        }
    
    def __call__(self, input: str) -> ToolOutput:
        """
        根据查询检索知识图谱中的相关信息
        
        参数:
            input: 用户查询文本
            
        返回:
            ToolOutput: 包含检索结果的工具输出对象
        """
        logger.info(f"执行知识图谱查询: {input}")
        try:
            # TODO: 实现知识图谱查询逻辑
            # 暂时返回空结果
            result = {
                "triples": [],
                "entities": [],
                "count": 0,
                "success": True
            }
            
            # 记录用户输入
            input_params = {
                "input": input
            }
            
            # 返回ToolOutput对象
            return ToolOutput(
                content=str(result),
                tool_name=self.metadata.name,
                raw_output=result,
                raw_input=input_params
            )
        except Exception as e:
            logger.error(f"知识图谱查询失败: {str(e)}")
            error_result = {
                "triples": [],
                "entities": [],
                "count": 0,
                "error": str(e),
                "success": False
            }
            
            # 记录用户输入
            input_params = {
                "input": input
            }
            
            # 错误情况也返回ToolOutput对象
            return ToolOutput(
                content=str(error_result),
                tool_name=self.metadata.name,
                raw_output=error_result,
                raw_input=input_params
            ) 