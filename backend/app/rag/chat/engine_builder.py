from typing import Optional, List

from sqlmodel import Session
from llama_index.core import ServiceContext
from llama_index.core.schema import NodeWithScore
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.tools import QueryEngineTool
from llama_index.core.query_engine.utils import get_response
from llama_index.core.tools.types import ToolMetadata
from llama_index.core.query_engine import CustomQueryEngine, RetrieverQueryEngine
from llama_index.core.tools.function_tool import FunctionTool
from llama_index.core.callbacks import CallbackManager
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.agent import FunctionCallingAgentWorker
from llama_index.core.agent import AgentRunner

from app.models.chat_engine import ChatEngine
from app.models.knowledge_base import KnowledgeBase
from app.rag.chat.config import ChatEngineConfig
# 使用try-except处理模块路径变化的导入问题
try:
    from app.rag.retrieval.retriever_builder import RetrieverBuilder
except ImportError:
    # 如果当前模块不存在，使用替代导入路径
    from app.rag.retrievers.chunk.builder import RetrieverBuilder

try:
    from app.rag.retrieval.rerank.reranker import Reranker
except ImportError:
    # 如果当前模块不存在，使用替代导入路径
    from app.rag.rerankers.llama_reranker import LlamaReranker as Reranker

try:
    from app.rag.llm_factory import create_llm, create_service_context
except ImportError:
    # 如果当前模块不存在，使用替代导入路径
    from app.rag.llms.factory import create_llm, create_service_context

from app.repositories import knowledge_base as kb_repo
from app.rag.tools.sql_query_tool import SQLQueryTool

class ChatEngineBuilder:
    """聊天引擎构建器"""

    def __init__(self, db_session: Session):
        """
        初始化
        
        参数:
            db_session: 数据库会话
        """
        self.db_session = db_session
        
    def _create_kb_engine(
        self, 
        service_context: ServiceContext, 
        kb: KnowledgeBase, 
        config: ChatEngineConfig,
        postprocessors: Optional[List[BaseNodePostprocessor]] = None
    ) -> QueryEngineTool:
        """
        创建知识库查询引擎
        
        参数:
            service_context: 服务上下文
            kb: 知识库
            config: 聊天引擎配置
            postprocessors: 节点后处理器列表
            
        返回:
            QueryEngineTool: 查询引擎工具
        """
        # 创建检索器
        retriever_builder = RetrieverBuilder(self.db_session)
        retriever = retriever_builder.build_from_kb_and_config(
            kb, 
            config
        )
        
        # 创建查询引擎
        node_engine = RetrieverQueryEngine.from_args(
            retriever=retriever,
            service_context=service_context,
            node_postprocessors=postprocessors or []
        )
        
        # 创建工具
        return QueryEngineTool(
            query_engine=node_engine,
            metadata=ToolMetadata(
                name=f"kb_{kb.id}",
                description=kb.description or f"知识库 - {kb.display_name}"
            )
        )
    
    def _create_sql_query_tool(
        self,
        config: ChatEngineConfig,
        service_context: ServiceContext,
    ) -> Optional[SQLQueryTool]:
        """
        创建SQL查询工具
        
        参数:
            config: 聊天引擎配置
            service_context: 服务上下文
            
        返回:
            Optional[SQLQueryTool]: 如果启用了数据库功能,返回SQL查询工具
        """
        # 检查数据库功能是否启用
        if not config.database.enabled:
            return None
            
        # 检查是否配置了数据库连接
        connections = config.get_linked_database_connections(self.db_session)
        if not connections:
            return None
            
        # 创建SQL查询工具
        return SQLQueryTool(
            db_session=self.db_session,
            config=config,
            llm=service_context.llm
        )
        
    def build_agent_runner(
        self,
        engine: ChatEngine,
        config: ChatEngineConfig,
        callback_manager: Optional[CallbackManager] = None,
    ) -> AgentRunner:
        """
        构建代理运行器
        
        参数:
            engine: 聊天引擎
            config: 聊天引擎配置
            callback_manager: 回调管理器
            
        返回:
            AgentRunner: 代理运行器
        """
        # 创建LLM和服务上下文
        llm = create_llm(config, callback_manager=callback_manager)
        service_context = create_service_context(config, llm, callback_manager)
        
        # 准备重排序器
        postprocessors = []
        if config.retrieval and config.retrieval.reranking and config.retrieval.reranking.enabled:
            reranker = Reranker(config.retrieval.reranking)
            postprocessors.append(reranker)
            
        # 构建工具列表
        tools = []
        
        # 添加知识库工具
        kbs = config.get_knowledge_bases(self.db_session)
        for kb in kbs:
            kb_tool = self._create_kb_engine(
                service_context=service_context,
                kb=kb,
                config=config,
                postprocessors=postprocessors
            )
            tools.append(kb_tool)
            
        # 添加SQL查询工具
        sql_tool = self._create_sql_query_tool(config, service_context)
        if sql_tool:
            tools.append(sql_tool)
            
        # TODO: 添加其他工具
        
        # 创建代理工作器
        system_prompt = config.llm.system_prompt
        react_chat_formatter = ReActChatFormatter(
            system_prompt=system_prompt
        )
        
        agent_worker = FunctionCallingAgentWorker.from_tools(
            tools=tools,
            llm=llm,
            system_prompt=system_prompt,
            verbose=True
        )
        
        # 创建代理运行器
        return AgentRunner(agent_worker=agent_worker)
        
    def build(
        self,
        engine: ChatEngine,
        config: ChatEngineConfig,
        callback_manager: Optional[CallbackManager] = None,
    ) -> AgentRunner:
        """
        构建聊天引擎
        
        参数:
            engine: 聊天引擎
            config: 聊天引擎配置
            callback_manager: 回调管理器
            
        返回:
            AgentRunner: 代理运行器
        """
        return self.build_agent_runner(engine, config, callback_manager) 