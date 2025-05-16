from typing import Dict, List, Optional
from pydantic import BaseModel, Field
import logging
import asyncio

from ..tools.base import BaseTool, ToolParameters, ToolResult

class KnowledgeGraphParameters(ToolParameters):
    """知识图谱工具参数"""
    query: str
    depth: int = 2
    include_meta: bool = True
    with_degree: bool = True

class KnowledgeGraphResult(ToolResult):
    """知识图谱工具结果"""
    context: str = ""
    entities: List[Dict] = Field(default_factory=list)
    relationships: List[Dict] = Field(default_factory=list)

class KnowledgeGraphTool(BaseTool[KnowledgeGraphParameters, KnowledgeGraphResult]):
    """知识图谱工具，用于查询知识图谱"""
    
    def __init__(self, db_session=None, engine_config=None):
        super().__init__(
            name="knowledge_graph_tool",
            description="从知识图谱中检索实体和关系信息",
            parameter_type=KnowledgeGraphParameters,
            result_type=KnowledgeGraphResult
        )
        self.db_session = db_session
        self.engine_config = engine_config
        self.kg_index = None
    
    async def execute(self, parameters: KnowledgeGraphParameters) -> KnowledgeGraphResult:
        """执行知识图谱查询"""
        self.logger.info(f"执行知识图谱查询: {parameters.query[:50]}...")
        
        try:
            # 检查知识图谱是否启用
            if not self.engine_config or not hasattr(self.engine_config, "knowledge_graph") or not self.engine_config.knowledge_graph.enabled:
                self.logger.info("知识图谱未启用")
                return KnowledgeGraphResult(
                    success=True,
                    context="",
                    entities=[],
                    relationships=[]
                )
            
            # 获取知识库
            knowledge_bases = self.engine_config.get_knowledge_bases(self.db_session)
            if not knowledge_bases:
                self.logger.warning("未找到知识库")
                return KnowledgeGraphResult(success=False, error_message="未找到知识库")
            
            # 导入必要的模块
            from app.rag.retrievers.knowledge_graph.fusion_retriever import KnowledgeGraphFusionRetriever
            from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrieverConfig
            
            # 创建知识图谱检索器
            kg_retriever = KnowledgeGraphFusionRetriever(
                db_session=self.db_session,
                knowledge_base_ids=[kb.id for kb in knowledge_bases],
                llm=self.engine_config.get_llama_llm(self.db_session),
                use_query_decompose=self.engine_config.knowledge_graph.using_intent_search,
                config=KnowledgeGraphRetrieverConfig(
                    depth=parameters.depth,
                    include_meta=parameters.include_meta,
                    with_degree=parameters.with_degree
                )
            )
            
            # 执行检索
            knowledge_graph = await self._run_async(
                kg_retriever.retrieve_knowledge_graph,
                parameters.query
            )
            
            # 生成知识图谱上下文
            context = ""
            if knowledge_graph:
                if self.engine_config.knowledge_graph.using_intent_search:
                    # 使用意图搜索模板
                    from llama_index.core.prompts.rich import RichPromptTemplate
                    if hasattr(self.engine_config.llm, "intent_graph_knowledge"):
                        kg_context_template = RichPromptTemplate(
                            self.engine_config.llm.intent_graph_knowledge
                        )
                        context = kg_context_template.format(
                            sub_queries=knowledge_graph.to_subqueries_dict(),
                        )
                else:
                    # 使用普通知识图谱模板
                    from llama_index.core.prompts.rich import RichPromptTemplate
                    if hasattr(self.engine_config.llm, "normal_graph_knowledge"):
                        kg_context_template = RichPromptTemplate(
                            self.engine_config.llm.normal_graph_knowledge
                        )
                        context = kg_context_template.format(
                            entities=knowledge_graph.entities,
                            relationships=knowledge_graph.relationships,
                        )
            
            # 返回结果
            return KnowledgeGraphResult(
                success=True,
                context=context,
                entities=[entity.model_dump() for entity in knowledge_graph.entities] if knowledge_graph else [],
                relationships=[rel.model_dump() for rel in knowledge_graph.relationships] if knowledge_graph else []
            )
            
        except Exception as e:
            self.logger.error(f"知识图谱查询出错: {str(e)}", exc_info=True)
            return KnowledgeGraphResult(
                success=False,
                error_message=f"知识图谱查询出错: {str(e)}"
            )
    
    async def _run_async(self, func, *args, **kwargs):
        """异步执行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 