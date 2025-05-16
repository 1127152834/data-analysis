import asyncio
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from datetime import datetime
import logging
import json

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex
from llama_index.core.prompts.rich import RichPromptTemplate

from ..context import Context
from ..events import Event, StartEvent, PrepEvent, KnowledgeEvent, ReasoningEvent, ResponseEvent
from ..workflow import step
from .base_agent import BaseAgent
from ..retrievers import KnowledgeRetriever
from ..tools.registry import ToolRegistry
from ..tools.database_query_tool import DatabaseQueryParameters
from app.rag.default_prompt import TOOL_DECISION_PROMPT, REASONING_ANALYSIS_PROMPT, HYBRID_RESPONSE_SYNTHESIS_PROMPT

# 添加专用日志器
logger = logging.getLogger("autoflow.agents")

class QAAgent(BaseAgent):
    """问答智能体，负责分析问题、调用工具和生成回答"""
    
    def __init__(self, 
                 db_session: Session = None, 
                 engine_config: Any = None, 
                 llm: LLM = None, 
                 fast_llm: LLM = None,
                 tool_registry: Optional[ToolRegistry] = None):
        super().__init__(
            name="QAAgent",
            description="负责分析问题、调用工具和生成回答的智能体",
            db_session=db_session, 
            engine_config=engine_config,
            tool_registry=tool_registry
        )
        self.llm = llm
        self.fast_llm = fast_llm
        self.knowledge_index = None  # 向量存储索引
        self.kg_index = None  # 知识图谱索引
        self.tool_registry = tool_registry  # 工具注册表
        
        # 创建知识检索工具实例
        logger.info("【QAAgent】初始化知识检索工具")
        self.retriever = KnowledgeRetriever(
            db_session=db_session,
            engine_config=engine_config,
            llm=llm,
            fast_llm=fast_llm
        )
        logger.info(f"【QAAgent】初始化完成, engine_config={engine_config is not None}, llm={llm is not None}, fast_llm={fast_llm is not None}, tool_registry={tool_registry is not None}")
    
    def set_indices(self, knowledge_index, kg_index=None):
        """设置索引实例"""
        logger.info(f"【QAAgent】设置索引: knowledge_index={knowledge_index is not None}, kg_index={kg_index is not None}")
        self.knowledge_index = knowledge_index
        self.kg_index = kg_index
        
        # 同时更新检索工具的索引
        self.retriever.vector_index = knowledge_index
        self.retriever.kg_index = kg_index
        logger.info("【QAAgent】索引设置完成")
        
    def set_tool_registry(self, tool_registry: ToolRegistry):
        """设置工具注册表"""
        logger.info(f"【QAAgent】设置工具注册表")
        self.tool_registry = tool_registry
        logger.info(f"【QAAgent】工具注册表设置完成，可用工具: {', '.join(tool_registry.list_tools())}")
    
    @step
    async def process(self, ctx: Context, event: Event) -> Event:
        """处理各类事件的主方法"""
        logger.info(f"【QAAgent】开始处理事件: {type(event).__name__}")
        
        if isinstance(event, PrepEvent):
            # 处理准备事件，负责检索知识
            return await self._handle_prep_event(ctx, event)
        elif isinstance(event, KnowledgeEvent):
            # 处理知识事件，负责分析并决定使用工具
            return await self._handle_knowledge_event(ctx, event)
        elif isinstance(event, ReasoningEvent):
            # 处理推理事件，负责生成最终回答
            return await self._handle_reasoning_event(ctx, event)
        
        logger.warning(f"【QAAgent】未处理的事件类型: {type(event).__name__}")
        return event  # 原样返回未处理的事件
    
    async def _handle_prep_event(self, ctx: Context, event: PrepEvent) -> Event:
        """处理准备事件，主要负责知识检索"""
        logger.info("【QAAgent】处理PrepEvent，开始知识检索")
        
        # 获取基本信息
        user_question = await ctx.get("user_question", "")
        refined_question = await ctx.get("refined_question", "")
        if not refined_question:
            refined_question = user_question
            logger.info(f"【QAAgent】使用原始问题: {user_question[:50]}...")
        else:
            logger.info(f"【QAAgent】使用优化问题: {refined_question[:50]}...")
            
        chat_history = await ctx.get("chat_history", [])
        logger.info(f"【QAAgent】聊天历史长度: {len(chat_history)}")
        
        # 解析并存储上下文
        knowledge_graph_context = ""
        retrieved_nodes = []
        
        # 通知前端开始知识检索
        logger.info("【QAAgent】发送前端通知: 开始知识检索")
        self.emit_info("检索相关知识...")
        
        # 步骤1: 先查询知识图谱(如果有)
        if self.kg_index:
            logger.info("【QAAgent】开始查询知识图谱")
            self.emit_info("查询知识图谱...")
            
            # 使用retriever查询知识图谱
            try:
                logger.info(f"【QAAgent】调用search_knowledge_graph, 问题: {refined_question[:50]}...")
                knowledge_graph_context = await self.retriever.search_knowledge_graph(refined_question)
                logger.info(f"【QAAgent】知识图谱检索完成，结果长度: {len(knowledge_graph_context)}")
                await ctx.set("knowledge_graph_context", knowledge_graph_context)
                
                # 如果有知识图谱结果，发送注释
                if knowledge_graph_context:
                    logger.info("【QAAgent】发送前端通知: 知识图谱查询结果")
                    self.emit_info("从知识图谱找到相关信息")
            except Exception as e:
                logger.error(f"【QAAgent错误】知识图谱查询出错: {str(e)}", exc_info=True)
        else:
            logger.info("【QAAgent】没有配置知识图谱索引，跳过知识图谱查询")
        
        # 步骤2: 检索向量库
        if self.knowledge_index:
            logger.info("【QAAgent】开始检索向量库")
            self.emit_info("搜索知识库...")
            
            # 使用retriever查询向量库
            try:
                logger.info(f"【QAAgent】调用search_vector_store, 问题: {refined_question[:50]}...")
                retrieved_nodes = await self.retriever.search_vector_store(refined_question)
                logger.info(f"【QAAgent】向量检索完成，结果数量: {len(retrieved_nodes)}")
                await ctx.set("knowledge_nodes", retrieved_nodes)
                
                # 发送检索结果信息
                self.emit_info(f"找到 {len(retrieved_nodes)} 条相关知识")
                
                # 发送头部知识源预览
                if retrieved_nodes:
                    preview_nodes = retrieved_nodes[:2]  # 只预览前2个结果
                    preview_text = "\n\n".join([
                        f"- {self._get_source_title(node)}: {node.get('text', '')[:100]}..."
                        for node in preview_nodes
                    ])
                    
                    logger.info(f"【QAAgent】发送知识预览: {preview_text[:200]}...")
                    self.emit_info(f"知识预览:\n{preview_text}")
            except Exception as e:
                logger.error(f"【QAAgent错误】向量检索出错: {str(e)}", exc_info=True)
                # 错误情况下，确保仍然继续流程
                self.emit_info("未找到相关知识")
        else:
            logger.info("【QAAgent】没有配置向量索引，跳过向量检索")
            
            # 没有向量索引的情况下，通知前端
            self.emit_info("系统未配置知识库")
        
        # 通知前端开始思考
        self.emit_info("思考中...")
        
        # 返回下一个事件
        logger.info(f"【QAAgent】知识检索完成，返回KnowledgeEvent事件, retrieved_nodes={len(retrieved_nodes)}, knowledge_graph_context长度={len(knowledge_graph_context)}")
        return KnowledgeEvent(
            knowledge_nodes=retrieved_nodes,
            knowledge_graph_context=knowledge_graph_context
        )
    
    async def _handle_knowledge_event(self, ctx: Context, event: KnowledgeEvent) -> Event:
        """处理知识事件，主要负责工具选择与执行"""
        logger.info("【QAAgent】处理KnowledgeEvent，开始分析问题和选择工具")
        
        # 获取必要信息
        user_question = await ctx.get("user_question", "")
        knowledge_nodes = event.knowledge_nodes
        knowledge_graph_context = event.knowledge_graph_context
        chat_history = await ctx.get("chat_history", [])
        
        # 从知识节点提取文本
        knowledge_texts = []
        for node in knowledge_nodes:
            if isinstance(node, dict) and "text" in node:
                knowledge_texts.append(node["text"])
        
        knowledge_context = "\n\n".join(knowledge_texts)
        
        # 通知前端开始思考
        self.emit_info("思考中...")
        
        # 检查是否有工具可用
        if not self.tool_registry or not self.tool_registry.list_tools():
            logger.info("【QAAgent】没有可用工具，直接进行推理")
            return ReasoningEvent(
                reasoning="无需使用特殊工具，直接基于已检索到的知识回答问题。",
                tool_calls=[],
                tool_results=[]
            )
        
        # 准备工具决策的上下文
        available_tools = self.tool_registry.list_tools()
        tool_descriptions = []
        
        for tool_name in available_tools:
            tool_instance = self.tool_registry.get_tool(tool_name)
            tool_descriptions.append({
                "name": tool_name,
                "description": tool_instance.description,
                "parameters": self._get_parameters_schema(tool_instance)
            })
        
        # 使用LLM决定工具使用
        try:
            tool_decision_template = RichPromptTemplate(TOOL_DECISION_PROMPT)
            tool_decision = await self._run_async(
                self.llm.predict,
                tool_decision_template,
                question=user_question,
                retrieved_context=knowledge_context,
                knowledge_graph_context=knowledge_graph_context,
                available_tools=json.dumps(tool_descriptions, ensure_ascii=False),
                chat_history=self._format_chat_history(chat_history)
            )
            
            logger.info(f"【QAAgent】工具决策结果: {tool_decision[:200]}...")
            
            # 解析决策结果
            tool_calls = self._parse_tool_calls(tool_decision)
            logger.info(f"【QAAgent】解析出的工具调用: {tool_calls}")
            
            if not tool_calls:
                logger.info("【QAAgent】未决定使用任何工具，直接进行推理")
                return ReasoningEvent(
                    reasoning="经过分析，无需使用特殊工具，直接基于已检索到的知识回答问题。",
                    tool_calls=[],
                    tool_results=[]
                )
            
            # 通知前端正在使用工具
            for tool_call in tool_calls:
                self.emit_info(f"正在使用工具: {tool_call['name']}")
            
            # 执行工具调用
            tool_results = []
            for tool_call in tool_calls:
                try:
                    logger.info(f"【QAAgent】执行工具调用: {tool_call['name']}")
                    tool_instance = self.tool_registry.get_tool(tool_call["name"])
                    
                    # 转换参数格式
                    tool_params = tool_call["parameters"]
                    
                    # 特殊处理，针对数据库查询工具添加查询模式
                    if tool_call["name"] == "database_query_tool" and "query_mode" not in tool_params:
                        # 默认使用router模式，更智能地选择查询引擎
                        tool_params["query_mode"] = "router"
                    
                    # 执行工具
                    result = await tool_instance.execute(tool_params)
                    tool_results.append({
                        "name": tool_call["name"],
                        "success": result.success,
                        "content": result.context if hasattr(result, "context") else str(result),
                        "error": result.error_message if hasattr(result, "error_message") and result.error_message else None
                    })
                    
                    logger.info(f"【QAAgent】工具调用结果: success={result.success}")
                    
                    # 通知前端工具执行结果
                    status = "成功" if result.success else "失败"
                    self.emit_info(f"工具 {tool_call['name']} 执行{status}")
                except Exception as e:
                    logger.error(f"【QAAgent错误】工具执行出错: {str(e)}", exc_info=True)
                    tool_results.append({
                        "name": tool_call["name"],
                        "success": False,
                        "content": "",
                        "error": f"工具执行出错: {str(e)}"
                    })
                    
                    # 通知前端工具执行失败
                    self.emit_error(f"工具 {tool_call['name']} 执行失败: {str(e)}")
            
            # 返回推理事件
            return ReasoningEvent(
                reasoning=tool_decision,
                tool_calls=tool_calls,
                tool_results=tool_results
            )
        
        except Exception as e:
            logger.error(f"【QAAgent错误】工具决策出错: {str(e)}", exc_info=True)
            return ReasoningEvent(
                reasoning=f"工具决策出错: {str(e)}",
                tool_calls=[],
                tool_results=[]
            )
    
    async def _handle_reasoning_event(self, ctx: Context, event: ReasoningEvent) -> Event:
        """处理推理事件，生成最终回答"""
        logger.info("【QAAgent】处理ReasoningEvent，开始生成最终回答")
        
        # 获取必要信息
        user_question = await ctx.get("user_question", "")
        knowledge_nodes = await ctx.get("knowledge_nodes", [])
        knowledge_graph_context = await ctx.get("knowledge_graph_context", "")
        chat_history = await ctx.get("chat_history", [])
        
        # 从知识节点提取文本
        knowledge_texts = []
        for node in knowledge_nodes:
            if isinstance(node, dict) and "text" in node:
                knowledge_texts.append(node["text"])
        
        knowledge_context = "\n\n".join(knowledge_texts)
        
        # 通知前端正在生成回答
        self.emit_info("正在生成回答...")
        
        try:
            # 分析工具结果
            tool_results = event.tool_results
            reasoning_analysis = ""
            
            if tool_results:
                # 使用LLM分析工具结果
                reasoning_template = RichPromptTemplate(REASONING_ANALYSIS_PROMPT)
                reasoning_analysis = await self._run_async(
                    self.llm.predict,
                    reasoning_template,
                    question=user_question,
                    reasoning=event.reasoning,
                    tool_results=json.dumps(tool_results, ensure_ascii=False)
                )
                logger.info(f"【QAAgent】工具结果分析: {reasoning_analysis[:200]}...")
            
            # 生成最终回答
            synthesis_template = RichPromptTemplate(HYBRID_RESPONSE_SYNTHESIS_PROMPT)
            final_answer = await self._run_async(
                self.llm.predict,
                synthesis_template,
                question=user_question,
                retrieved_context=knowledge_context,
                knowledge_graph_context=knowledge_graph_context,
                reasoning=event.reasoning,
                reasoning_analysis=reasoning_analysis,
                tool_results=json.dumps(tool_results, ensure_ascii=False),
                chat_history=self._format_chat_history(chat_history)
            )
            
            logger.info(f"【QAAgent】生成最终回答: {final_answer[:200]}...")
            
            # 通知前端回答生成完成
            self.emit_info("回答已生成")
            
            # 返回响应事件
            return ResponseEvent(
                response=final_answer
            )
        
        except Exception as e:
            logger.error(f"【QAAgent错误】生成回答出错: {str(e)}", exc_info=True)
            
            # 生成一个错误回答
            error_response = f"抱歉，在回答您的问题时遇到了技术问题。请稍后再试或联系系统管理员。(错误: {str(e)})"
            
            return ResponseEvent(
                response=error_response
            )
    
    def _get_source_title(self, node: Dict) -> str:
        """从节点中提取源标题"""
        if not node or not isinstance(node, dict):
            return "Unknown"
            
        metadata = node.get("metadata", {})
        if metadata:
            # 按优先级尝试不同的元数据字段
            for field in ["title", "source", "file_name", "file_path"]:
                if field in metadata and metadata[field]:
                    return str(metadata[field])
                    
        return "Unknown Source"
    
    def _format_chat_history(self, chat_history: List) -> str:
        """将聊天历史格式化为字符串"""
        if not chat_history:
            return ""
            
        history_str = ""
        for msg in chat_history:
            role = msg.get("role", "unknown").lower()
            content = msg.get("content", "")
            
            if role == "user":
                history_str += f"User: {content}\n"
            elif role in ["assistant", "ai", "system"]:
                history_str += f"Assistant: {content}\n"
                
        return history_str.strip()
    
    def _parse_tool_calls(self, tool_decision: str) -> List[Dict]:
        """解析工具决策文本，提取工具调用"""
        tool_calls = []
        
        # 尝试解析JSON格式的工具调用
        try:
            # 查找JSON块
            import re
            json_match = re.search(r'```json\n(.*?)\n```', tool_decision, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(1)
                parsed = json.loads(json_str)
                
                if isinstance(parsed, list):
                    tool_calls = parsed
                elif isinstance(parsed, dict) and "tools" in parsed:
                    tool_calls = parsed["tools"]
                elif isinstance(parsed, dict):
                    # 单个工具调用
                    tool_calls = [parsed]
                    
            # 如果没有找到JSON块，尝试直接解析整个字符串
            if not tool_calls:
                try:
                    parsed = json.loads(tool_decision)
                    if isinstance(parsed, list):
                        tool_calls = parsed
                    elif isinstance(parsed, dict) and "tools" in parsed:
                        tool_calls = parsed["tools"]
                    elif isinstance(parsed, dict):
                        # 单个工具调用
                        tool_calls = [parsed]
                except:
                    pass
        except Exception as e:
            logger.error(f"【QAAgent错误】解析工具调用出错: {str(e)}", exc_info=True)
        
        # 验证工具调用格式
        valid_tool_calls = []
        for call in tool_calls:
            if isinstance(call, dict) and "name" in call and "parameters" in call:
                # 确保工具名称在注册表中
                if self.tool_registry and self.tool_registry.has_tool(call["name"]):
                    valid_tool_calls.append(call)
                else:
                    logger.warning(f"【QAAgent】未注册的工具: {call['name']}")
        
        return valid_tool_calls
    
    def _get_parameters_schema(self, tool) -> Dict:
        """获取工具参数的schema"""
        if hasattr(tool, "parameter_type") and tool.parameter_type:
            # 尝试获取参数类型的schema
            schema = {}
            for field_name, field in tool.parameter_type.__annotations__.items():
                schema[field_name] = str(field)
            return schema
        return {}
    
    async def _run_async(self, func, *args, **kwargs):
        """将同步函数异步运行"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 