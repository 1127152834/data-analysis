from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging
import asyncio
import re

from ..tools.base import BaseTool, ToolParameters, ToolResult

class KnowledgeRetrievalParameters(ToolParameters):
    """知识检索工具参数"""
    query: str
    top_k: int = 5
    reranker_enabled: bool = True
    similarity_top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    metadata_filters: Optional[Dict[str, Any]] = None
    enable_rewrite: bool = True
    use_enhanced_query: bool = True
    max_query_length: int = 1024
    
class KnowledgeRetrievalResult(ToolResult):
    """知识检索工具结果"""
    context: str = ""
    sources: List[Dict] = Field(default_factory=list)
    
class KnowledgeRetrievalTool(BaseTool[KnowledgeRetrievalParameters, KnowledgeRetrievalResult]):
    """知识检索工具，用于从知识库检索上下文"""
    
    def __init__(self, db_session=None, engine_config=None):
        super().__init__(
            name="knowledge_retrieval_tool",
            description="从知识库中检索上下文信息",
            parameter_type=KnowledgeRetrievalParameters,
            result_type=KnowledgeRetrievalResult
        )
        self.db_session = db_session
        self.engine_config = engine_config
        
    async def execute(self, parameters: KnowledgeRetrievalParameters) -> KnowledgeRetrievalResult:
        """执行知识检索"""
        self.logger.info(f"执行知识检索: {parameters.query[:50]}...")
        
        try:
            # 检查知识库是否启用
            if not self.engine_config or not hasattr(self.engine_config, "kb_retrieval") or not self.engine_config.kb_retrieval.enabled:
                self.logger.info("知识库检索未启用")
                return KnowledgeRetrievalResult(
                    success=True,
                    context="",
                    sources=[]
                )
            
            # 获取知识库
            knowledge_bases = self.engine_config.get_knowledge_bases(self.db_session)
            if not knowledge_bases:
                self.logger.warning("未找到知识库")
                return KnowledgeRetrievalResult(success=False, error_message="未找到知识库")
            
            # 处理查询字符串
            query = parameters.query
            if parameters.max_query_length and len(query) > parameters.max_query_length:
                query = query[:parameters.max_query_length]
                self.logger.warning(f"查询过长，已截断至{parameters.max_query_length}字符")
            
            # 导入必要的模块
            from app.rag.retrievers.hybrid_retriever import HybridRetriever
            from app.rag.retrievers.schema import RetrieverConfig
            
            # 创建检索配置
            retriever_config = RetrieverConfig(
                top_k=parameters.top_k,
                reranker_enabled=parameters.reranker_enabled,
                similarity_top_k=parameters.similarity_top_k,
                similarity_threshold=parameters.similarity_threshold,
                use_enhanced_query=parameters.use_enhanced_query,
            )
            
            # 创建检索器
            retriever = HybridRetriever(
                db_session=self.db_session,
                knowledge_base_ids=[kb.id for kb in knowledge_bases],
                llm=self.engine_config.get_llama_llm(self.db_session),
                config=retriever_config,
            )
            
            # 执行检索
            if parameters.enable_rewrite:
                retrieval_result = await self._run_async(
                    retriever.retrieve_with_rewrite,
                    query,
                    parameters.metadata_filters
                )
            else:
                retrieval_result = await self._run_async(
                    retriever.retrieve,
                    query,
                    parameters.metadata_filters
                )
            
            # 生成上下文
            context = ""
            if retrieval_result and retrieval_result.contexts:
                context = self._format_contexts(retrieval_result.contexts)
            
            # 格式化来源
            sources = []
            if retrieval_result and retrieval_result.contexts:
                for ctx in retrieval_result.contexts:
                    source = {
                        "title": ctx.metadata.get("title", ""),
                        "url": ctx.metadata.get("url", ""),
                        "file_name": ctx.metadata.get("file_name", ""),
                        "score": ctx.score,
                        "id": ctx.id,
                    }
                    sources.append(source)
            
            # 返回结果
            return KnowledgeRetrievalResult(
                success=True,
                context=context,
                sources=sources
            )
            
        except Exception as e:
            self.logger.error(f"知识检索出错: {str(e)}", exc_info=True)
            return KnowledgeRetrievalResult(
                success=False,
                error_message=f"知识检索出错: {str(e)}"
            )
    
    def _format_contexts(self, contexts):
        """格式化上下文"""
        formatted_text = ""
        for i, ctx in enumerate(contexts):
            content = ctx.text
            metadata = ctx.metadata
            
            # 添加段落编号
            formatted_text += f"---段落{i+1}---\n"
            
            # 添加来源信息
            if metadata.get("title"):
                formatted_text += f"标题: {metadata.get('title')}\n"
            if metadata.get("url"):
                formatted_text += f"链接: {metadata.get('url')}\n"
            if metadata.get("file_name"):
                formatted_text += f"文件: {metadata.get('file_name')}\n"
            
            # 添加内容
            formatted_text += f"内容:\n{content}\n\n"
        
        return formatted_text
    
    async def _run_async(self, func, *args, **kwargs):
        """异步执行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 