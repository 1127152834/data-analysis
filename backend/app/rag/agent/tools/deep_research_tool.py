"""
深度研究工具模块

提供对复杂问题进行深入研究的工具，通过多轮检索和思考来提高回答质量
"""

import logging
from typing import Dict, List, Optional, Any

from llama_index.core.tools.types import BaseTool, ToolMetadata, ToolOutput
from llama_index.core.llms.llm import LLM
from sqlmodel import Session

from app.rag.chat.config import ChatEngineConfig

logger = logging.getLogger(__name__)

# 深度研究提示词模板
DEEP_RESEARCH_PROMPT = """你是一个高级研究助手，需要对复杂问题进行深入分析。
基于初步发现，你需要进一步深入思考并回答更深层次的问题。

# 用户原始问题
{original_question}

# 初步发现
{initial_findings}

请进行以下深度研究步骤：
1. 分析初步发现中的关键点和潜在知识缺口
2. 提出至少3个需要进一步探索的子问题
3. 对于初步发现中的模糊或可能有误的信息，进行批判性分析
4. 对各个子问题提供深入、全面的回答
5. 综合分析，形成对原始问题的深度见解

你的回答应该比初步发现更加深入、全面、有洞察力。确保使用专业且准确的语言，提供有价值的新信息。
"""

class DeepResearchTool(BaseTool):
    """
    深度研究工具
    
    对复杂问题进行深入分析，通过多轮检索和思考提高回答质量
    """
    
    def __init__(
        self,
        db_session: Session,
        engine_config: ChatEngineConfig,
        llm: Optional[LLM] = None,
        description: str = "对复杂问题进行深入研究，提供更全面深入的答案",
        prompt_template: str = DEEP_RESEARCH_PROMPT
    ):
        """
        初始化深度研究工具
        
        参数:
            db_session: 数据库会话对象
            engine_config: 聊天引擎配置
            llm: 语言模型，如果为None则使用engine_config中的模型
            description: 工具描述
            prompt_template: 深度研究提示词模板
        """
        self.db_session = db_session
        self.engine_config = engine_config
        self.llm = llm if llm else engine_config.get_llama_llm(db_session)
        self.prompt_template = prompt_template
        
        # 直接设置元数据
        self._metadata = ToolMetadata(name="deep_research", description=description)
    
    @property
    def metadata(self) -> ToolMetadata:
        """返回工具的元数据信息"""
        return self._metadata
    
    def __call__(self, query_str: str, initial_findings: str) -> ToolOutput:
        """
        对问题进行深度研究
        
        参数:
            query_str: 用户原始问题
            initial_findings: 初步发现/回答
            
        返回:
            ToolOutput: 包含深度研究结果的工具输出对象
        """
        logger.info(f"执行深度研究: {query_str}")
        try:
            # 格式化提示词
            prompt = self.prompt_template.format(
                original_question=query_str,
                initial_findings=initial_findings
            )
            
            # 使用LLM生成深度研究结果
            response = self.llm.complete(prompt)
            
            # 构建结果
            result = {
                "deep_research_result": response.text,
                "original_question": query_str,
                "initial_findings": initial_findings,
                "success": True
            }
            
            # 记录用户输入
            input_params = {
                "query_str": query_str,
                "initial_findings": initial_findings
            }
            
            # 返回ToolOutput对象
            return ToolOutput(
                content=response.text,
                tool_name=self.metadata.name,
                raw_output=result,
                raw_input=input_params
            )
        except Exception as e:
            logger.error(f"深度研究失败: {str(e)}")
            error_result = {
                "deep_research_result": f"深度研究时出错: {str(e)}",
                "original_question": query_str,
                "initial_findings": initial_findings,
                "error": str(e),
                "success": False
            }
            
            # 记录用户输入
            input_params = {
                "query_str": query_str,
                "initial_findings": initial_findings
            }
            
            # 错误情况也返回ToolOutput对象
            return ToolOutput(
                content=f"深度研究时出错: {str(e)}",
                tool_name=self.metadata.name,
                raw_output=error_result,
                raw_input=input_params
            ) 