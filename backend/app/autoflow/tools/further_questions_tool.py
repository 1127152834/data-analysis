from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import logging
import asyncio

from ..tools.base import BaseTool, ToolParameters, ToolResult

class FurtherQuestionsParameters(ToolParameters):
    """后续问题推荐工具参数"""
    query: str
    context: str
    response: str
    question_count: int = 3
    
class FurtherQuestionsResult(ToolResult):
    """后续问题推荐工具结果"""
    questions: List[str] = Field(default_factory=list)
    
class FurtherQuestionsTool(BaseTool[FurtherQuestionsParameters, FurtherQuestionsResult]):
    """后续问题推荐工具，用于生成相关的后续问题"""
    
    def __init__(self, db_session=None, engine_config=None):
        super().__init__(
            name="further_questions_tool",
            description="生成相关的后续问题建议",
            parameter_type=FurtherQuestionsParameters,
            result_type=FurtherQuestionsResult
        )
        self.db_session = db_session
        self.engine_config = engine_config
        
    async def execute(self, parameters: FurtherQuestionsParameters) -> FurtherQuestionsResult:
        """生成后续问题"""
        self.logger.info(f"生成后续问题: {parameters.query[:50]}...")
        
        try:
            # 检查后续问题推荐是否启用
            if not self.engine_config or not hasattr(self.engine_config, "further_questions") or not self.engine_config.further_questions.enabled:
                self.logger.info("后续问题推荐未启用")
                return FurtherQuestionsResult(
                    success=True,
                    questions=[]
                )
            
            # 导入必要的模块
            from app.rag.further_questions.generator import FurtherQuestionsGenerator
            from app.rag.further_questions.schema import FurtherQuestionsGeneratorConfig
            
            # 获取LLM
            llm = self.engine_config.get_llama_llm(self.db_session)
            
            # 创建后续问题生成器
            config = FurtherQuestionsGeneratorConfig(
                model_name=self.engine_config.further_questions.model_name,
                temperature=self.engine_config.further_questions.temperature,
                max_tokens=self.engine_config.further_questions.max_tokens,
                top_p=self.engine_config.further_questions.top_p,
                question_count=parameters.question_count
            )
            
            generator = FurtherQuestionsGenerator(
                llm=llm,
                config=config
            )
            
            # 生成后续问题
            questions = await self._run_async(
                generator.generate,
                parameters.query,
                parameters.context,
                parameters.response
            )
            
            # 返回结果
            return FurtherQuestionsResult(
                success=True,
                questions=questions if questions else []
            )
            
        except Exception as e:
            self.logger.error(f"生成后续问题出错: {str(e)}", exc_info=True)
            return FurtherQuestionsResult(
                success=False,
                error_message=f"生成后续问题出错: {str(e)}"
            )
    
    async def _run_async(self, func, *args, **kwargs):
        """异步执行同步函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 