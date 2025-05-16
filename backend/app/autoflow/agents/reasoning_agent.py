from typing import Any, Dict, List, Optional, Union, AsyncGenerator
import asyncio
import logging

from sqlalchemy.orm import Session
from llama_index.core.llms import LLM
from llama_index.core.llms import ChatMessage, MessageRole

from ..context import Context
from ..events import Event, KnowledgeEvent, ReasoningEvent, ResponseEvent, StreamEvent
from ..workflow import step
from .base_agent import BaseAgent

class ReasoningAgent(BaseAgent):
    """推理Agent，负责分析信息、推理和决策"""
    
    def __init__(self, db_session: Session = None, engine_config: Any = None, llm: LLM = None, fast_llm: LLM = None):
        super().__init__(
            name="ReasoningAgent",
            description="负责分析信息、推理和决策的智能体",
            db_session=db_session, 
            engine_config=engine_config
        )
        self.llm = llm
        self.fast_llm = fast_llm
        # 初始化工具
        self.tools = []
        if engine_config and hasattr(engine_config, "get_tools"):
            self.tools = engine_config.get_tools()
        
        # 增加日志记录
        logger = logging.getLogger("autoflow.agents")
        self.logger = logger
        logger.info(f"【ReasoningAgent】初始化完成, llm={llm is not None}, fast_llm={fast_llm is not None}, tools={len(self.tools)}")
    
    async def process(self, ctx: Context, event: Event) -> Union[Event, AsyncGenerator[Event, None]]:
        """通用处理方法"""
        self.logger.info(f"【ReasoningAgent】开始处理事件: {type(event).__name__}")
        
        if isinstance(event, KnowledgeEvent):
            self.logger.info("【ReasoningAgent】处理KnowledgeEvent事件，调用analyze_knowledge方法")
            return await self.analyze_knowledge(ctx, event)
        elif isinstance(event, ReasoningEvent):
            self.logger.info("【ReasoningAgent】处理ReasoningEvent事件，调用make_decisions方法")
            return await self.make_decisions(ctx, event)
        
        self.logger.warning(f"【ReasoningAgent】未处理的事件类型: {type(event).__name__}")
        return ResponseEvent(answer="")
    
    @step(event_type=KnowledgeEvent)
    async def analyze_knowledge(self, ctx: Context, ev: KnowledgeEvent) -> ReasoningEvent:
        """分析检索到的知识，生成推理结论"""
        self.logger.info("【ReasoningAgent】开始分析检索到的知识")
        
        # 获取用户问题、知识点和知识图谱上下文
        refined_question = await ctx.get("refined_question", "")
        if not refined_question:
            refined_question = await ctx.get("user_question", "")
            self.logger.info(f"【ReasoningAgent】使用原始问题: {refined_question[:50]}...")
        else:
            self.logger.info(f"【ReasoningAgent】使用优化问题: {refined_question[:50]}...")
            
        knowledge_nodes = ev.knowledge_nodes
        knowledge_graph_context = ev.knowledge_graph_context
        
        self.logger.info(f"【ReasoningAgent】知识节点数量: {len(knowledge_nodes)}, 知识图谱上下文长度: {len(knowledge_graph_context)}")
        
        # 通知前端开始推理
        self.logger.info("【ReasoningAgent】通知前端开始推理")
        self.emit_info("分析检索到的知识...")
        
        # 构建推理上下文
        self.logger.info("【ReasoningAgent】开始构建知识上下文")
        knowledge_context = await self._build_knowledge_context(knowledge_nodes, knowledge_graph_context)
        self.logger.info(f"【ReasoningAgent】知识上下文构建完成，长度: {len(knowledge_context)}")
        await ctx.set("knowledge_context", knowledge_context)
        
        # 生成推理结论
        self.logger.info("【ReasoningAgent】开始生成推理结论")
        reasoning_result = await self._generate_reasoning(refined_question, knowledge_context)
        self.logger.info(f"【ReasoningAgent】推理结论生成完成，长度: {len(reasoning_result)}")
        await ctx.set("reasoning_result", reasoning_result)
        
        # 通知前端推理完成
        self.logger.info("【ReasoningAgent】通知前端推理完成")
        self.emit_info("知识分析完成")
        
        # 返回推理事件
        self.logger.info("【ReasoningAgent】返回ReasoningEvent事件")
        return ReasoningEvent(
            reasoning_result=reasoning_result
        )
    
    @step(event_type=ReasoningEvent)
    async def make_decisions(self, ctx: Context, ev: ReasoningEvent) -> Union[ResponseEvent, AsyncGenerator[Event, None]]:
        """基于推理结果，做出决策并生成最终回答"""
        self.logger.info("【ReasoningAgent】开始决策并生成回答")
        
        # 获取用户问题和推理结果
        refined_question = await ctx.get("refined_question", "")
        if not refined_question:
            refined_question = await ctx.get("user_question", "")
            
        reasoning_result = ev.reasoning_result
        self.logger.info(f"【ReasoningAgent】用户问题: {refined_question[:50]}..., 推理结果长度: {len(reasoning_result)}")
        
        # 通知前端开始生成回答
        self.logger.info("【ReasoningAgent】通知前端开始生成回答")
        self.emit_info("生成回答...")
        
        # 检查是否需要使用工具
        self.logger.info("【ReasoningAgent】检查是否需要使用工具")
        tool_calls = await self._check_tool_calls(refined_question, reasoning_result)
        self.logger.info(f"【ReasoningAgent】工具检查结果: {len(tool_calls)} 个工具调用")
        
        # 流式生成处理
        is_streaming = self.engine_config and hasattr(self.engine_config, "streaming_enabled") and self.engine_config.streaming_enabled
        self.logger.info(f"【ReasoningAgent】流式生成设置: is_streaming={is_streaming}")
        
        # 如果需要使用工具
        if tool_calls:
            self.logger.info(f"【ReasoningAgent】需要使用工具，将执行 {len(tool_calls)} 个工具调用")
            # 通知前端工具调用
            self.emit_info("正在使用工具...")
            
            # 执行工具调用
            try:
                self.logger.info("【ReasoningAgent】开始执行工具调用")
                tool_results = await self._execute_tool_calls(tool_calls)
                self.logger.info(f"【ReasoningAgent】工具调用执行完成，返回 {len(tool_results)} 个结果")
            
                # 记录工具调用结果
                await ctx.set("tool_calls", tool_calls)
                await ctx.set("tool_results", tool_results)
                
                # 通知前端工具调用结果
                self.emit_info(f"工具调用结果:\n{chr(10).join([f'{result.get('tool_name', '未知工具')} - {result.get('result', '无结果')}' for result in tool_results])}")
            except Exception as e:
                self.logger.error(f"【ReasoningAgent错误】工具调用执行失败: {str(e)}", exc_info=True)
                tool_results = [{"tool_name": "error", "status": "error", "result": f"工具调用失败: {str(e)}"}]
            
            # 基于工具调用结果生成最终回答
            if is_streaming:
                # 流式生成回答
                self.logger.info("【ReasoningAgent】开始流式生成带工具的回答")
                generator = self._generate_stream_answer_with_tools(refined_question, reasoning_result, tool_results)
                
                # 生成事件流
                event_count = 0
                async for event in generator:
                    event_count += 1
                    self.logger.debug(f"【ReasoningAgent】生成流式事件 #{event_count}: {type(event).__name__}")
                    yield event
                
                self.logger.info(f"【ReasoningAgent】流式生成带工具的回答完成，共生成 {event_count} 个事件")
            else:
                # 非流式生成回答
                self.logger.info("【ReasoningAgent】开始非流式生成带工具的回答")
                answer = await self._generate_answer_with_tools(refined_question, reasoning_result, tool_results)
                self.logger.info(f"【ReasoningAgent】非流式生成带工具的回答完成，回答长度: {len(answer)}")
                
                # 通知前端回答生成完成
                self.emit_info("回答生成完成")
                
                # 更新结果到上下文
                await ctx.set("answer", answer)
                
                # 返回响应事件
                self.logger.info("【ReasoningAgent】返回ResponseEvent事件")
                yield ResponseEvent(answer=answer)
        else:
            # 不需要工具，直接生成回答
            self.logger.info("【ReasoningAgent】不需要使用工具，直接生成回答")
            if is_streaming:
                # 流式生成回答
                self.logger.info("【ReasoningAgent】开始流式生成回答")
                generator = self._generate_stream_answer(refined_question, reasoning_result)
                
                # 生成事件流
                event_count = 0
                async for event in generator:
                    event_count += 1
                    self.logger.debug(f"【ReasoningAgent】生成流式事件 #{event_count}: {type(event).__name__}")
                    yield event
                
                self.logger.info(f"【ReasoningAgent】流式生成回答完成，共生成 {event_count} 个事件")
            else:
                # 非流式生成回答
                self.logger.info("【ReasoningAgent】开始非流式生成回答")
                answer = await self._generate_answer(refined_question, reasoning_result)
                self.logger.info(f"【ReasoningAgent】非流式生成回答完成，回答长度: {len(answer)}")
                
                # 通知前端回答生成完成
                self.emit_info("回答生成完成")
                
                # 更新结果到上下文
                await ctx.set("answer", answer)
                
                # 返回响应事件
                self.logger.info("【ReasoningAgent】返回ResponseEvent事件")
                yield ResponseEvent(answer=answer)
        
        # 如果是流式生成，则没有直接返回值，这里设置一个默认ResponseEvent
        # 注意：这段代码只会在流式生成的情况下执行
        if is_streaming:
            # 这不是yield，是return，所以不会有语法错误
            self.logger.info("【ReasoningAgent】流式生成完成，返回空的ResponseEvent")
            yield ResponseEvent(answer="")
    
    async def _build_knowledge_context(self, knowledge_nodes: List[Dict], knowledge_graph_context: str) -> str:
        """
        构建知识上下文
        
        参数:
            knowledge_nodes: 知识节点列表
            knowledge_graph_context: 知识图谱上下文
            
        返回:
            str: 组合后的知识上下文
        """
        # 构建节点上下文
        node_texts = []
        for i, node in enumerate(knowledge_nodes, 1):
            node_text = node.get("text", "")
            node_score = node.get("score", 0.0)
            
            # 提取元数据
            metadata = node.get("metadata", {})
            source = metadata.get("file_name", metadata.get("source", "未知来源"))
            
            # 格式化节点上下文
            node_context = f"[文档{i} 相似度:{node_score:.2f} 来源:{source}]\n{node_text}"
            node_texts.append(node_context)
        
        # 组合所有上下文
        full_context = ""
        
        if node_texts:
            full_context += "### 相关文档\n" + "\n\n".join(node_texts)
        
        if knowledge_graph_context:
            if full_context:
                full_context += "\n\n"
            full_context += "### " + knowledge_graph_context
        
        if not full_context:
            full_context = "没有找到相关知识。"
        
        return full_context
    
    async def _generate_reasoning(self, question: str, knowledge_context: str) -> str:
        """
        生成推理结论
        
        参数:
            question: 用户问题
            knowledge_context: 知识上下文
            
        返回:
            str: 推理结论
        """
        if not self.llm:
            return "无法执行推理，LLM未初始化。"
        
        try:
            # 构建提示
            messages = []
            
            # 添加系统提示
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content="你是一个专业的分析师。你的任务是分析提供的信息，提取关键事实，并形成有逻辑的推理结论。不要直接回答用户问题，只需分析信息并总结关键点。你的分析将用于后续回答生成。"
            ))
            
            # 添加用户问题和知识上下文
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=f"请基于以下信息，对问题\"{question}\"进行分析，提取关键事实，并给出推理结论：\n\n{knowledge_context}"
            ))
            
            # 调用LLM
            response = await self.llm.achat(messages)
            reasoning = response.message.content.strip()
            
            return reasoning
            
        except Exception as e:
            # 如果推理过程中出错，返回简单推理结果
            return f"基于检索到的信息，无法形成完整推理。错误: {str(e)}"
    
    async def _check_tool_calls(self, question: str, reasoning: str) -> List[Dict]:
        """
        检查是否需要调用工具
        
        参数:
            question: 用户问题
            reasoning: 推理结果
            
        返回:
            List[Dict]: 工具调用列表，如果不需要调用则为空列表
        """
        # 如果没有工具，直接返回空列表
        if not self.tools:
            return []
        
        # 如果没有LLM，无法决策，返回空列表
        if not self.llm:
            return []
        
        try:
            # 构建工具描述
            tool_descriptions = []
            for i, tool in enumerate(self.tools, 1):
                name = getattr(tool, "name", f"工具{i}")
                description = getattr(tool, "description", "未提供描述")
                tool_descriptions.append(f"{name}: {description}")
            
            # 如果没有有效工具描述，返回空列表
            if not tool_descriptions:
                return []
            
            # 构建提示
            messages = []
            
            # 添加系统提示
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content=f"""你是一个决策专家，需要决定是否使用工具来帮助回答用户问题。
可用工具列表：
{chr(10).join(tool_descriptions)}

仅当用户问题明确需要使用特定工具且推理结论表明需要额外信息时才调用工具。
如果决定调用工具，返回JSON格式的工具调用列表：[{{\"tool_name\": \"工具名称\", \"tool_args\": {{\"参数名\": \"参数值\"}}}}]
如果不需要调用工具，返回空列表: []"""
            ))
            
            # 添加用户问题和推理结论
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=f"用户问题: {question}\n\n推理结论: {reasoning}\n\n是否需要使用工具？如需使用，请指定工具和参数。"
            ))
            
            # 调用LLM
            response = await self.llm.achat(messages)
            decision = response.message.content.strip()
            
            # 尝试解析JSON响应
            import json
            try:
                # 提取JSON部分（可能嵌入在解释中）
                json_start = decision.find('[')
                json_end = decision.rfind(']') + 1
                
                if json_start >= 0 and json_end > json_start:
                    json_str = decision[json_start:json_end]
                    tool_calls = json.loads(json_str)
                    return tool_calls if isinstance(tool_calls, list) else []
                return []
            except Exception:
                # JSON解析失败，尝试使用简单规则提取
                if "tool_name" in decision and "tool_args" in decision:
                    # 简单启发式提取
                    try:
                        tool_name_start = decision.find("tool_name") + 11  # len("tool_name") + 2 (": )
                        tool_name_end = decision.find("\"", tool_name_start)
                        tool_name = decision[tool_name_start:tool_name_end].strip()
                        
                        return [{"tool_name": tool_name, "tool_args": {}}]
                    except Exception:
                        return []
                return []
                
        except Exception as e:
            # 如果决策过程中出错，返回空列表
            return []
    
    async def _execute_tool_calls(self, tool_calls: List[Dict]) -> List[Dict]:
        """
        执行工具调用
        
        参数:
            tool_calls: 工具调用列表
            
        返回:
            List[Dict]: 工具调用结果列表
        """
        results = []
        
        for call in tool_calls:
            try:
                # 提取工具名称和参数
                tool_name = call.get("tool_name", "")
                tool_args = call.get("tool_args", {})
                
                # 查找对应的工具
                tool = None
                for t in self.tools:
                    if getattr(t, "name", "") == tool_name:
                        tool = t
                        break
                
                if not tool:
                    # 工具未找到
                    results.append({
                        "tool_name": tool_name,
                        "status": "error",
                        "result": "工具未找到"
                    })
                    continue
                
                # 执行工具调用
                tool_result = tool(**tool_args)
                
                # 提取结果
                result_content = ""
                if hasattr(tool_result, "content"):
                    result_content = tool_result.content
                elif hasattr(tool_result, "raw_output"):
                    result_content = str(tool_result.raw_output)
                else:
                    result_content = str(tool_result)
                
                # 添加结果
                results.append({
                    "tool_name": tool_name,
                    "status": "success",
                    "result": result_content
                })
                
            except Exception as e:
                # 处理工具调用异常
                results.append({
                    "tool_name": call.get("tool_name", "未知工具"),
                    "status": "error",
                    "result": f"执行出错: {str(e)}"
                })
        
        return results
    
    async def _generate_answer(self, question: str, reasoning: str) -> str:
        """
        生成最终回答
        
        参数:
            question: 用户问题
            reasoning: 推理结果
            
        返回:
            str: 生成的回答
        """
        if not self.llm:
            return "无法生成回答，LLM未初始化。"
        
        try:
            # 构建提示
            messages = []
            
            # 添加系统提示
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content="你是一个专业的助手。你的任务是基于分析结果，生成清晰、准确、有帮助的回答。回答应该直接解决用户问题，提供有用信息，并保持专业的语气。"
            ))
            
            # 添加用户问题和推理结论
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=f"请基于以下分析结果，直接回答问题\"{question}\"：\n\n分析结果: {reasoning}"
            ))
            
            # 调用LLM
            response = await self.llm.achat(messages)
            answer = response.message.content.strip()
            
            return answer
            
        except Exception as e:
            # 如果回答生成过程中出错，返回简单回答
            return f"抱歉，我无法提供完整回答。错误: {str(e)}"
    
    async def _generate_answer_with_tools(self, question: str, reasoning: str, tool_results: List[Dict]) -> str:
        """
        基于工具调用结果生成最终回答
        
        参数:
            question: 用户问题
            reasoning: 推理结果
            tool_results: 工具调用结果
            
        返回:
            str: 生成的回答
        """
        if not self.llm:
            return "无法生成回答，LLM未初始化。"
        
        try:
            # 构建工具结果描述
            tool_results_text = []
            for result in tool_results:
                tool_name = result.get("tool_name", "未知工具")
                status = result.get("status", "未知状态")
                result_content = result.get("result", "无结果")
                
                tool_result_text = f"工具: {tool_name}\n状态: {status}\n结果: {result_content}"
                tool_results_text.append(tool_result_text)
            
            # 构建提示
            messages = []
            
            # 添加系统提示
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content="你是一个专业的助手。你的任务是基于分析结果和工具调用结果，生成清晰、准确、有帮助的回答。回答应该直接解决用户问题，整合工具提供的信息，并保持专业的语气。"
            ))
            
            # 添加用户问题、推理结论和工具结果
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=f"请基于以下分析结果和工具调用结果，直接回答问题\"{question}\"：\n\n分析结果: {reasoning}\n\n工具调用结果:\n{chr(10).join(tool_results_text)}"
            ))
            
            # 调用LLM
            response = await self.llm.achat(messages)
            answer = response.message.content.strip()
            
            return answer
            
        except Exception as e:
            # 如果回答生成过程中出错，返回简单回答
            return f"抱歉，我无法提供完整回答。错误: {str(e)}"
    
    async def _generate_stream_answer(self, question: str, reasoning: str) -> AsyncGenerator[Event, None]:
        """
        流式生成最终回答
        
        参数:
            question: 用户问题
            reasoning: 推理结果
            
        返回:
            AsyncGenerator[Event, None]: 流式事件生成器
        """
        if not self.llm:
            yield self._emit_stream_event("无法生成回答，LLM未初始化。")
            return
        
        try:
            # 构建提示
            messages = []
            
            # 添加系统提示
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content="你是一个专业的助手。你的任务是基于分析结果，生成清晰、准确、有帮助的回答。回答应该直接解决用户问题，提供有用信息，并保持专业的语气。"
            ))
            
            # 添加用户问题和推理结论
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=f"请基于以下分析结果，直接回答问题\"{question}\"：\n\n分析结果: {reasoning}"
            ))
            
            # 调用LLM并流式处理响应
            response_gen = await self.llm.astream_chat(messages)
            
            answer_buffer = ""
            async for chunk in response_gen:
                if hasattr(chunk, 'delta') and chunk.delta:
                    # 发送流式事件
                    yield self._emit_stream_event(chunk.delta)
                    answer_buffer += chunk.delta
            
            # 更新上下文
            # 这里需要获取Context，但流式生成器中无法直接传递ctx
            # 可以通过全局状态管理或后续处理解决
            
        except Exception as e:
            # 如果回答生成过程中出错，返回简单回答
            error_msg = f"抱歉，我无法提供完整回答。错误: {str(e)}"
            yield self._emit_stream_event(error_msg)
    
    async def _generate_stream_answer_with_tools(self, question: str, reasoning: str, tool_results: List[Dict]) -> AsyncGenerator[Event, None]:
        """
        基于工具调用结果流式生成最终回答
        
        参数:
            question: 用户问题
            reasoning: 推理结果
            tool_results: 工具调用结果
            
        返回:
            AsyncGenerator[Event, None]: 流式事件生成器
        """
        if not self.llm:
            yield self._emit_stream_event("无法生成回答，LLM未初始化。")
            return
        
        try:
            # 构建工具结果描述
            tool_results_text = []
            for result in tool_results:
                tool_name = result.get("tool_name", "未知工具")
                status = result.get("status", "未知状态")
                result_content = result.get("result", "无结果")
                
                tool_result_text = f"工具: {tool_name}\n状态: {status}\n结果: {result_content}"
                tool_results_text.append(tool_result_text)
            
            # 构建提示
            messages = []
            
            # 添加系统提示
            messages.append(ChatMessage(
                role=MessageRole.SYSTEM,
                content="你是一个专业的助手。你的任务是基于分析结果和工具调用结果，生成清晰、准确、有帮助的回答。回答应该直接解决用户问题，整合工具提供的信息，并保持专业的语气。"
            ))
            
            # 添加用户问题、推理结论和工具结果
            messages.append(ChatMessage(
                role=MessageRole.USER,
                content=f"请基于以下分析结果和工具调用结果，直接回答问题\"{question}\"：\n\n分析结果: {reasoning}\n\n工具调用结果:\n{chr(10).join(tool_results_text)}"
            ))
            
            # 调用LLM并流式处理响应
            response_gen = await self.llm.astream_chat(messages)
            
            answer_buffer = ""
            async for chunk in response_gen:
                if hasattr(chunk, 'delta') and chunk.delta:
                    # 发送流式事件
                    yield self._emit_stream_event(chunk.delta)
                    answer_buffer += chunk.delta
            
            # 更新上下文
            # 这里需要获取Context，但流式生成器中无法直接传递ctx
            # 可以通过全局状态管理或后续处理解决
            
        except Exception as e:
            # 如果回答生成过程中出错，返回简单回答
            error_msg = f"抱歉，我无法提供完整回答。错误: {str(e)}"
            yield self._emit_stream_event(error_msg)
    
    async def _generate_answer_event(self, ctx: Context, ev: ReasoningEvent) -> ResponseEvent:
        """非流式生成回答并返回响应事件，用于测试"""
        # 获取用户问题和推理结果
        refined_question = await ctx.get("refined_question", "")
        if not refined_question:
            refined_question = await ctx.get("user_question", "")
            
        reasoning_result = ev.reasoning_result
        
        # 通知前端开始生成回答
        self.emit_info("生成回答...")
        
        # 生成回答（简化版，不使用工具）
        answer = await self._generate_answer(refined_question, reasoning_result)
        
        # 通知前端回答生成完成
        self.emit_info("回答生成完成")
        
        # 更新结果到上下文
        await ctx.set("answer", answer)
        
        # 返回响应事件
        return ResponseEvent(answer=answer)