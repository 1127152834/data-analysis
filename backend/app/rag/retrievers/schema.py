"""检索器模块的模型定义"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import uuid

class RetrieverConfig(BaseModel):
    """检索器配置"""
    top_k: int = 5
    reranker_enabled: bool = True
    similarity_top_k: Optional[int] = None
    similarity_threshold: Optional[float] = None
    use_enhanced_query: bool = True

class Context(BaseModel):
    """检索上下文"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0

class RetrievalResult(BaseModel):
    """检索结果"""
    query: str
    rewritten_query: Optional[str] = None
    contexts: List[Context] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict) 