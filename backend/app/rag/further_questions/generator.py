"""后续问题生成器模块，用于生成相关的后续问题"""

from typing import List, Optional
import logging
from llama_index.core.llms import LLM

from .schema import FurtherQuestionsGeneratorConfig

logger = logging.getLogger("app.rag.further_questions.generator")

class FurtherQuestionsGenerator:
    """后续问题生成器，用于生成相关的后续问题"""
    
    def __init__(self, llm: LLM, config: FurtherQuestionsGeneratorConfig):
        """初始化后续问题生成器
        
        参数:
            llm: 大语言模型实例
            config: 后续问题生成器配置
        """
        self.llm = llm
        self.config = config
        self.logger = logger
    
    def generate(self, query: str, context: str, response: str) -> List[str]:
        """生成后续问题
        
        参数:
            query: 用户原始问题
            context: 检索到的上下文
            response: 系统对用户问题的回答
            
        返回:
            生成的后续问题列表
        """
        try:
            # 生成提示模板
            prompt = self._create_prompt(query, context, response)
            
            # 调用LLM生成后续问题
            completion = self.llm.complete(
                prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                top_p=self.config.top_p
            )
            
            # 解析LLM输出，提取问题
            questions = self._parse_questions(completion.text)
            
            # 限制问题数量
            if len(questions) > self.config.question_count:
                questions = questions[:self.config.question_count]
                
            return questions
            
        except Exception as e:
            self.logger.error(f"生成后续问题时出错: {str(e)}", exc_info=True)
            return []
    
    def _create_prompt(self, query: str, context: str, response: str) -> str:
        """创建生成后续问题的提示模板
        
        参数:
            query: 用户原始问题
            context: 检索到的上下文
            response: 系统对用户问题的回答
            
        返回:
            提示模板字符串
        """
        prompt = f"""基于以下信息，生成 {self.config.question_count} 个相关的后续问题，这些问题应该是用户可能会对该主题感兴趣的深入问题。

用户原始问题：
{query}

系统回答：
{response}

"""
        # 如果上下文不为空，添加上下文信息
        if context and len(context.strip()) > 0:
            context_summary = context
            if len(context) > 1000:
                # 简化上下文，只使用前1000个字符
                context_summary = context[:1000] + "...(缩略)"
                
            prompt += f"""
相关上下文：
{context_summary}
"""

        prompt += """
请直接列出问题，每个问题单独成行，不要添加编号或任何额外标记，例如：
如何提高查询效率？
有哪些常见的优化技巧？
如何解决内存溢出问题？
"""
        
        return prompt
    
    def _parse_questions(self, text: str) -> List[str]:
        """从LLM输出中解析问题
        
        参数:
            text: LLM的输出文本
            
        返回:
            解析出的问题列表
        """
        # 分行并过滤空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # 过滤掉非问题的行（如标题、说明等）
        questions = []
        for line in lines:
            # 判断是否是问题（以问号结尾或包含疑问词）
            if line.endswith('?') or line.endswith('？') or any(q in line for q in ['什么', '如何', '为什么', '怎么', '哪些', '是否']):
                questions.append(line)
                
        return questions 