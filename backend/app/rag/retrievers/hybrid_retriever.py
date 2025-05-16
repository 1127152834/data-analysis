"""混合检索器，结合向量检索和关键词检索"""

from typing import Dict, List, Optional, Any
import logging
from sqlalchemy.orm import Session
from llama_index.core.llms import LLM

from .schema import RetrieverConfig, RetrievalResult, Context

logger = logging.getLogger("app.rag.retrievers.hybrid_retriever")

class HybridRetriever:
    """混合检索器，结合向量检索和关键词检索"""
    
    def __init__(
        self, 
        db_session: Session, 
        knowledge_base_ids: List[str], 
        llm: LLM = None,
        config: RetrieverConfig = None
    ):
        """初始化混合检索器
        
        参数:
            db_session: 数据库会话
            knowledge_base_ids: 知识库ID列表
            llm: 大语言模型实例
            config: 检索器配置
        """
        self.db_session = db_session
        self.knowledge_base_ids = knowledge_base_ids
        self.llm = llm
        self.config = config or RetrieverConfig()
        self.logger = logger
    
    def retrieve(self, query: str, metadata_filters: Optional[Dict[str, Any]] = None) -> RetrievalResult:
        """检索上下文
        
        参数:
            query: 查询字符串
            metadata_filters: 元数据过滤器
            
        返回:
            检索结果
        """
        try:
            # 这里应该实现实际的检索逻辑
            # 在实际系统中，应该使用向量数据库和关键词索引进行混合检索
            # 简化实现，仅返回模拟数据
            contexts = self._mock_retrieve(query, metadata_filters)
            
            return RetrievalResult(
                query=query,
                contexts=contexts
            )
            
        except Exception as e:
            self.logger.error(f"检索出错: {str(e)}", exc_info=True)
            return RetrievalResult(
                query=query,
                contexts=[]
            )
    
    def retrieve_with_rewrite(self, query: str, metadata_filters: Optional[Dict[str, Any]] = None) -> RetrievalResult:
        """使用查询重写进行检索
        
        参数:
            query: 查询字符串
            metadata_filters: 元数据过滤器
            
        返回:
            检索结果
        """
        try:
            # 查询重写，使用LLM优化原始查询
            rewritten_query = self._rewrite_query(query)
            
            # 使用重写后的查询进行检索
            orig_result = self.retrieve(query, metadata_filters)
            rewritten_result = None
            
            if rewritten_query and rewritten_query != query:
                rewritten_result = self.retrieve(rewritten_query, metadata_filters)
            
            # 合并结果
            if rewritten_result and rewritten_result.contexts:
                # 创建新的结果对象
                merged_contexts = self._merge_contexts(
                    orig_result.contexts, 
                    rewritten_result.contexts,
                    self.config.top_k
                )
                
                return RetrievalResult(
                    query=query,
                    rewritten_query=rewritten_query,
                    contexts=merged_contexts
                )
            
            # 如果重写查询未返回结果，使用原始查询结果
            return orig_result
            
        except Exception as e:
            self.logger.error(f"使用查询重写进行检索出错: {str(e)}", exc_info=True)
            return RetrievalResult(
                query=query,
                contexts=[]
            )
    
    def _rewrite_query(self, query: str) -> Optional[str]:
        """重写查询字符串
        
        参数:
            query: 原始查询字符串
            
        返回:
            重写后的查询字符串
        """
        if not self.llm or not self.config.use_enhanced_query:
            return None
            
        try:
            # 使用LLM重写查询
            prompt = f"""请重写以下查询，使其更适合向量检索。保持查询的原始意图，但可以添加相关术语和上下文。
原始查询: {query}

重写后的查询:"""
            
            response = self.llm.complete(prompt)
            rewritten_query = response.text.strip()
            
            # 确保重写后的查询不为空
            if not rewritten_query:
                return query
                
            return rewritten_query
            
        except Exception as e:
            self.logger.error(f"重写查询出错: {str(e)}", exc_info=True)
            return query
    
    def _merge_contexts(
        self, 
        orig_contexts: List[Context], 
        rewritten_contexts: List[Context], 
        max_contexts: int
    ) -> List[Context]:
        """合并两组上下文
        
        参数:
            orig_contexts: 原始查询的上下文
            rewritten_contexts: 重写查询的上下文
            max_contexts: 最大上下文数量
            
        返回:
            合并后的上下文列表
        """
        # 创建ID到Context的映射，用于去重
        merged_dict = {ctx.id: ctx for ctx in orig_contexts}
        
        # 添加重写查询的上下文，避免重复
        for ctx in rewritten_contexts:
            if ctx.id not in merged_dict:
                merged_dict[ctx.id] = ctx
                
        # 将合并后的上下文按得分排序
        merged_contexts = sorted(
            list(merged_dict.values()), 
            key=lambda x: x.score, 
            reverse=True
        )
        
        # 限制上下文数量
        if len(merged_contexts) > max_contexts:
            merged_contexts = merged_contexts[:max_contexts]
            
        return merged_contexts
    
    def _mock_retrieve(self, query: str, metadata_filters: Optional[Dict[str, Any]] = None) -> List[Context]:
        """模拟检索，返回示例数据
        
        参数:
            query: 查询字符串
            metadata_filters: 元数据过滤器
            
        返回:
            上下文列表
        """
        # 创建模拟上下文
        contexts = []
        
        # 添加一些示例上下文
        contexts.append(Context(
            text=f"这是与查询 '{query}' 相关的第一个模拟上下文。",
            metadata={
                "title": "示例文档1",
                "url": "https://example.com/doc1",
                "file_name": "example1.pdf",
                "source": "知识库1"
            },
            score=0.95
        ))
        
        contexts.append(Context(
            text=f"这是与查询 '{query}' 相关的第二个模拟上下文，包含一些技术细节。",
            metadata={
                "title": "示例文档2",
                "url": "https://example.com/doc2",
                "file_name": "example2.pdf",
                "source": "知识库2"
            },
            score=0.85
        ))
        
        contexts.append(Context(
            text=f"这是与查询 '{query}' 相关的第三个模拟上下文，提供了一些背景信息。",
            metadata={
                "title": "示例文档3",
                "url": "https://example.com/doc3",
                "file_name": "example3.pdf",
                "source": "知识库1"
            },
            score=0.75
        ))
        
        # 应用元数据过滤（简化实现）
        if metadata_filters:
            filtered_contexts = []
            for ctx in contexts:
                match = True
                for key, value in metadata_filters.items():
                    if key in ctx.metadata and ctx.metadata[key] != value:
                        match = False
                        break
                if match:
                    filtered_contexts.append(ctx)
            contexts = filtered_contexts
            
        return contexts 