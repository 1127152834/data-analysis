"""
响应生成工具模块

提供基于检索结果生成回答的工具
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator

from llama_index.core.schema import NodeWithScore
from llama_index.core.tools.types import BaseTool, ToolMetadata, ToolOutput
from llama_index.core import get_response_synthesizer
from llama_index.core.prompts.rich import RichPromptTemplate
from sqlmodel import Session

from app.rag.chat.config import ChatEngineConfig
from app.rag.chat.retrieve.retrieve_flow import SourceDocument

logger = logging.getLogger(__name__)

class ResponseGeneratorTool(BaseTool):
    """
    响应生成工具
    
    根据检索到的上下文生成回答
    """
    
    def __init__(
        self,
        db_session: Session,
        engine_config: ChatEngineConfig,
        description: str = "根据检索到的知识生成回答",
    ):
        """
        初始化响应生成工具
        
        参数:
            db_session: 数据库会话对象
            engine_config: 聊天引擎配置
            description: 工具描述
        """
        self.db_session = db_session
        self.engine_config = engine_config
        self.llm = engine_config.get_llama_llm(db_session)
        
        # 直接设置元数据
        self._metadata = ToolMetadata(name="response_generator", description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        """返回工具的元数据信息"""
        return self._metadata
    
    def _prepare_nodes(self, context_data: List[Dict]) -> List[NodeWithScore]:
        """
        将前端友好的上下文格式转换回NodeWithScore对象
        
        参数:
            context_data: 上下文数据字典列表
            
        返回:
            List[NodeWithScore]: 节点对象列表
        """
        from llama_index.core.schema import TextNode
        
        nodes = []
        for item in context_data:
            # 创建文本节点
            node = TextNode(
                text=item.get("text", ""),
                metadata=item.get("metadata", {}),
                id_=item.get("id")
            )
            # 创建带分数的节点
            node_with_score = NodeWithScore(
                node=node,
                score=item.get("score", 1.0)
            )
            nodes.append(node_with_score)
        
        return nodes
    
    def _get_source_documents(self, nodes: List[NodeWithScore]) -> List[SourceDocument]:
        """
        从节点创建源文档对象
        
        参数:
            nodes: 节点列表
            
        返回:
            List[SourceDocument]: 源文档列表
        """
        source_documents = []
        for node in nodes:
            metadata = node.node.metadata
            if not metadata:
                continue
                
            source_doc = SourceDocument(
                page_content=node.node.text,
                metadata=metadata
            )
            source_documents.append(source_doc)
            
        return source_documents
    
    def __call__(
        self, 
        user_question: str, 
        context_data: List[Dict], 
        knowledge_graph_context: str = "",
        stream: bool = False
    ) -> ToolOutput:
        """
        根据上下文生成回答
        
        参数:
            user_question: 用户查询
            context_data: 上下文数据（检索结果）
            knowledge_graph_context: 知识图谱上下文
            stream: 是否流式生成
            
        返回:
            ToolOutput: 生成的回答及相关信息的工具输出对象
        """
        logger.info(f"生成问题 '{user_question}' 的回答")
        try:
            # 将上下文转换为节点
            nodes = self._prepare_nodes(context_data)
            
            # 初始化响应合成器
            text_qa_template = RichPromptTemplate(
                template_str=self.engine_config.llm.text_qa_prompt
            )
            # 部分格式化模板，填入固定参数
            text_qa_template = text_qa_template.partial_format(
                current_date=datetime.now().strftime("%Y-%m-%d"),  # 当前日期
                graph_knowledges=knowledge_graph_context,  # 知识图谱上下文
                original_question=user_question,  # 原始问题
            )
            
            # 获取响应合成器
            response_synthesizer = get_response_synthesizer(
                llm=self.llm,  # 使用主LLM
                text_qa_template=text_qa_template,  # 问答模板
                streaming=stream  # 是否流式输出
            )

            # 使用响应合成器生成回答
            response = response_synthesizer.synthesize(
                query=user_question,  # 查询
                nodes=nodes,  # 相关文档块
            )
            
            # 获取源文档
            source_documents = self._get_source_documents(nodes)
            
            # 记录用户输入
            input_params = {
                "user_question": user_question,
                "context_data": context_data,
                "knowledge_graph_context": knowledge_graph_context,
                "stream": stream
            }
            
            # 如果是流式响应，返回生成器
            if stream and hasattr(response, "get_response_gen"):
                # 提取生成器
                response_text = ""
                response_gen = response.get_response_gen()
                
                # 构建结果
                result = {
                    "response_text": response.response,
                    "source_documents": [doc.metadata for doc in source_documents],
                    "response_gen": response_gen,  # 注意：这个生成器需要在agent层面特殊处理
                    "success": True
                }
                
                # 返回ToolOutput对象
                return ToolOutput(
                    content=response.response,
                    tool_name=self.metadata.name,
                    raw_output=result,
                    raw_input=input_params
                )
            
            # 构建正常结果
            result = {
                "response_text": response.response,
                "source_documents": [doc.metadata for doc in source_documents],
                "success": True
            }
            
            # 返回ToolOutput对象
            return ToolOutput(
                content=response.response,
                tool_name=self.metadata.name,
                raw_output=result,
                raw_input=input_params
            )
            
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            error_result = {
                "response_text": f"生成回答时出错: {str(e)}",
                "source_documents": [],
                "error": str(e),
                "success": False
            }
            
            # 记录用户输入
            input_params = {
                "user_question": user_question,
                "context_data": context_data,
                "knowledge_graph_context": knowledge_graph_context,
                "stream": stream
            }
            
            # 错误情况也返回ToolOutput对象
            return ToolOutput(
                content=f"生成回答时出错: {str(e)}",
                tool_name=self.metadata.name,
                raw_output=error_result,
                raw_input=input_params
            ) 