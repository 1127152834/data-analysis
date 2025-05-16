"""后续问题生成器模块的模型定义"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class FurtherQuestionsGeneratorConfig(BaseModel):
    """后续问题生成器配置"""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.95
    question_count: int = 3 