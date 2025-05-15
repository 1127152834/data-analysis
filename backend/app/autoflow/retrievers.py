import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any, Union
import asyncio

from sqlmodel import Session
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, QueryBundle
from llama_index.core.prompts.rich import RichPromptTemplate
from llama_index.core.indices import VectorStoreIndex
from llama_index.core.indices.knowledge_graph import KnowledgeGraphIndex
from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrieverConfig

from app.rag.retrievers.knowledge_graph.schema import KnowledgeGraphRetrievalResult
from app.rag.retrievers.knowledge_graph.fusion_retriever import KnowledgeGraphFusionRetriever
from app.rag.retrievers.chunk.fusion_retriever import ChunkFusionRetriever

# 增强日志记录
logger = logging.getLogger("autoflow.retrievers")

class KnowledgeRetriever:
    """知识检索工具类，负责知识图谱和向量检索"""
    
    def __init__(
        self,
        db_session: Session = None,
        engine_config: Any = None,
        llm: LLM = None,
        fast_llm: LLM = None,
        vector_index: VectorStoreIndex = None,
        kg_index: KnowledgeGraphIndex = None,
    ):
        """初始化知识检索工具
        
        参数:
            db_session: 数据库会话
            engine_config: 引擎配置
            llm: 语言模型
            fast_llm: 快速语言模型
            vector_index: 向量索引
            kg_index: 知识图谱索引
        """
        self.db_session = db_session
        self.engine_config = engine_config
        self.llm = llm
        self.fast_llm = fast_llm
        self.vector_index = vector_index
        self.kg_index = kg_index
        
        logger.info("【KnowledgeRetriever】初始化知识检索工具")
        logger.info(f"【KnowledgeRetriever】初始化参数: db_session={db_session is not None}, engine_config={engine_config is not None}, llm={llm is not None}, fast_llm={fast_llm is not None}")
        logger.info(f"【KnowledgeRetriever】索引状态: vector_index={vector_index is not None}, kg_index={kg_index is not None}")
        
        # 获取知识库IDs
        self.knowledge_base_ids = []
        if engine_config and hasattr(engine_config, "get_knowledge_bases"):
            try:
                knowledge_bases = engine_config.get_knowledge_bases(db_session)
                self.knowledge_base_ids = [kb.id for kb in knowledge_bases]
                logger.info(f"【KnowledgeRetriever】成功获取知识库IDs: {self.knowledge_base_ids}")
            except Exception as e:
                logger.error(f"【KnowledgeRetriever错误】获取知识库列表失败: {str(e)}", exc_info=True)
        else:
            logger.warning("【KnowledgeRetriever】engine_config不存在或没有get_knowledge_bases方法")
    
    async def search_knowledge_graph(self, query: str) -> str:
        """查询知识图谱并返回结构化上下文
        
        参数:
            query: 查询问题
            
        返回:
            str: 知识图谱上下文
        """
        logger.info(f"【KnowledgeRetriever】开始知识图谱搜索，查询: {query[:50]}...")
        
        if not self.db_session or not self.knowledge_base_ids:
            logger.warning("【KnowledgeRetriever】无法执行知识图谱搜索: db_session或knowledge_base_ids为空")
            return ""
        
        kg_context = ""
        try:
            # 检查知识图谱是否启用
            kg_config = None
            if hasattr(self.engine_config, "knowledge_graph"):
                kg_config = self.engine_config.knowledge_graph
                logger.info(f"【KnowledgeRetriever】知识图谱配置: enabled={getattr(kg_config, 'enabled', False)}, using_intent_search={getattr(kg_config, 'using_intent_search', False)}")
            
            # 如果启用了知识图谱，创建检索器
            if kg_config and getattr(kg_config, "enabled", False):
                using_intent_search = getattr(kg_config, "using_intent_search", False)
                
                # 创建配置对象
                config_dict = {}
                if hasattr(kg_config, "model_dump"):
                    config_dict = kg_config.model_dump(exclude={"enabled", "using_intent_search"})
                
                logger.info("【KnowledgeRetriever】创建知识图谱检索器")
                # 创建知识图谱检索器
                kg_retriever = KnowledgeGraphFusionRetriever(
                    db_session=self.db_session,
                    knowledge_base_ids=self.knowledge_base_ids,
                    llm=self.llm,
                    use_query_decompose=using_intent_search,
                    config=KnowledgeGraphRetrieverConfig.model_validate(config_dict)
                    if config_dict else KnowledgeGraphRetrieverConfig(),
                )
                
                # 执行知识图谱检索
                logger.info("【KnowledgeRetriever】执行知识图谱检索")
                knowledge_graph = await self._run_async(
                    kg_retriever.retrieve_knowledge_graph,
                    query
                )
                
                # 生成知识图谱上下文
                if knowledge_graph:
                    logger.info("【KnowledgeRetriever】成功检索到知识图谱，生成上下文")
                    kg_context = await self._get_knowledge_graph_context(knowledge_graph)
                    logger.info(f"【KnowledgeRetriever】知识图谱上下文生成完成，长度: {len(kg_context)}")
                else:
                    logger.info("【KnowledgeRetriever】知识图谱检索未返回结果")
            
            return kg_context
        except Exception as e:
            logger.error(f"【KnowledgeRetriever错误】知识图谱查询出错: {str(e)}", exc_info=True)
            return ""
    
    async def _get_knowledge_graph_context(self, knowledge_graph: KnowledgeGraphRetrievalResult) -> str:
        """根据知识图谱检索结果生成上下文
        
        参数:
            knowledge_graph: 知识图谱检索结果
            
        返回:
            str: 格式化的知识图谱上下文
        """
        logger.info("【KnowledgeRetriever】开始根据知识图谱检索结果生成上下文")
        
        if not self.engine_config or not hasattr(self.engine_config, "knowledge_graph"):
            logger.warning("【KnowledgeRetriever】无法生成知识图谱上下文: engine_config不存在或没有knowledge_graph属性")
            return ""
        
        try:
            kg_config = self.engine_config.knowledge_graph
            using_intent_search = getattr(kg_config, "using_intent_search", False)
            logger.info(f"【KnowledgeRetriever】知识图谱上下文生成配置: using_intent_search={using_intent_search}")
            
            if using_intent_search:
                # 使用意图搜索模板
                if hasattr(self.engine_config.llm, "intent_graph_knowledge"):
                    logger.info("【KnowledgeRetriever】使用意图搜索模板生成上下文")
                    kg_context_template = RichPromptTemplate(
                        self.engine_config.llm.intent_graph_knowledge
                    )
                    result = kg_context_template.format(
                        sub_queries=knowledge_graph.to_subqueries_dict(),
                    )
                    logger.info(f"【KnowledgeRetriever】意图搜索上下文生成完成，长度: {len(result)}")
                    return result
            else:
                # 使用普通知识图谱模板
                if hasattr(self.engine_config.llm, "normal_graph_knowledge"):
                    logger.info("【KnowledgeRetriever】使用普通知识图谱模板生成上下文")
                    kg_context_template = RichPromptTemplate(
                        self.engine_config.llm.normal_graph_knowledge
                    )
                    result = kg_context_template.format(
                        entities=knowledge_graph.entities,
                        relationships=knowledge_graph.relationships,
                    )
                    logger.info(f"【KnowledgeRetriever】普通知识图谱上下文生成完成，长度: {len(result)}")
                    return result
            
            logger.warning("【KnowledgeRetriever】找不到合适的知识图谱上下文模板")
            return ""
        except Exception as e:
            logger.error(f"【KnowledgeRetriever错误】生成知识图谱上下文出错: {str(e)}", exc_info=True)
            return ""
    
    async def refine_query(self, query: str, kg_context: str = "", chat_history: List = None) -> str:
        """优化查询问题
        
        参数:
            query: 原始查询
            kg_context: 知识图谱上下文
            chat_history: 聊天历史
            
        返回:
            str: 优化后的查询
        """
        logger.info(f"【KnowledgeRetriever】开始优化查询: {query[:50]}...")
        
        if not self.fast_llm or not hasattr(self.engine_config, "llm"):
            logger.warning("【KnowledgeRetriever】无法优化查询: fast_llm不存在或engine_config.llm不存在")
            return query
        
        try:
            # 获取优化问题的提示词模板
            prompt_template = None
            if hasattr(self.engine_config.llm, "condense_question_prompt"):
                logger.info("【KnowledgeRetriever】使用配置中的condense_question_prompt")
                prompt_template = RichPromptTemplate(
                    self.engine_config.llm.condense_question_prompt
                )
            else:
                # 使用默认提示词模板
                logger.info("【KnowledgeRetriever】使用默认问题优化提示词模板")
                default_prompt = """
                今天是 {current_date}。
                
                已知的知识图谱信息:
                {graph_knowledges}
                
                用户的问题是: {question}
                
                请分析用户的问题，并将问题重新表述为更清晰、更容易检索的形式，保留所有关键信息。
                重新表述的问题:
                """
                prompt_template = RichPromptTemplate(template_str=default_prompt)
            
            # 执行预测
            logger.info("【KnowledgeRetriever】调用LLM执行查询优化")
            refined_query = self.fast_llm.predict(
                prompt_template,
                graph_knowledges=kg_context,
                question=query,
                current_date=datetime.now().strftime("%Y-%m-%d")
            )
            
            # 处理结果
            refined = refined_query.strip().strip(".\"'!") if refined_query else query
            logger.info(f"【KnowledgeRetriever】查询优化完成，原始查询: {query[:30]}..., 优化后: {refined[:30]}...")
            return refined
            
        except Exception as e:
            logger.error(f"【KnowledgeRetriever错误】查询优化出错: {str(e)}", exc_info=True)
            return query
    
    async def search_vector_store(self, query: str, top_k: int = 5) -> List[Dict]:
        """向量检索
        
        参数:
            query: 查询问题
            top_k: 返回结果数量
            
        返回:
            List[Dict]: 检索结果列表
        """
        logger.info(f"【KnowledgeRetriever】开始向量检索，查询: {query[:50]}..., top_k={top_k}")
        
        if not self.db_session or not self.knowledge_base_ids:
            logger.warning("【KnowledgeRetriever】无法执行向量检索: db_session或knowledge_base_ids为空")
            return []
        
        try:
            # 确定检索参数
            similarity_top_k = top_k
            if hasattr(self.engine_config, "vector_search") and hasattr(self.engine_config.vector_search, "similarity_top_k"):
                similarity_top_k = self.engine_config.vector_search.similarity_top_k
                logger.info(f"【KnowledgeRetriever】使用配置的similarity_top_k={similarity_top_k}")
            
            # 创建向量检索器
            logger.info("【KnowledgeRetriever】创建ChunkFusionRetriever实例")
            retriever = ChunkFusionRetriever(
                db_session=self.db_session,
                knowledge_base_ids=self.knowledge_base_ids,
                llm=self.llm,
                config=self.engine_config.vector_search if hasattr(self.engine_config, "vector_search") else None,
                use_query_decompose=False,
            )
            
            # 执行检索
            logger.info("【KnowledgeRetriever】执行向量检索")
            try:
                nodes = await self._run_async(
                    retriever.retrieve,
                    QueryBundle(query)
                )
                logger.info(f"【KnowledgeRetriever】向量检索完成，原始结果数量: {len(nodes)}")
            except Exception as inner_e:
                logger.error(f"【KnowledgeRetriever错误】执行retrieve方法失败: {str(inner_e)}", exc_info=True)
                # 返回空列表，避免整个流程失败
                return []
            
            # 处理检索结果
            result_nodes = []
            for node in nodes:
                try:
                    if hasattr(node, "node") and hasattr(node, "score"):
                        # NodeWithScore类型
                        node_dict = {
                            "text": node.node.text,
                            "score": node.score,
                            "metadata": node.node.metadata
                        }
                        result_nodes.append(node_dict)
                    elif hasattr(node, "text") and hasattr(node, "metadata"):
                        # 直接是Node对象
                        node_dict = {
                            "text": node.text,
                            "score": 1.0,  # 默认相似度
                            "metadata": node.metadata
                        }
                        result_nodes.append(node_dict)
                    elif isinstance(node, dict):
                        # 已经是字典格式
                        result_nodes.append(node)
                    logger.debug(f"【KnowledgeRetriever】处理节点: {type(node).__name__}, 转换成功")
                except Exception as node_e:
                    logger.error(f"【KnowledgeRetriever错误】处理节点失败: {str(node_e)}, 节点类型: {type(node).__name__}", exc_info=True)
                    # 继续处理下一个节点
                    continue
            
            logger.info(f"【KnowledgeRetriever】向量检索结果处理完成，最终结果数量: {len(result_nodes)}")
            
            # 即使没有结果，也返回一个空列表
            if not result_nodes:
                logger.warning("【KnowledgeRetriever】没有找到相关的向量检索结果")
            
            return result_nodes
            
        except Exception as e:
            logger.error(f"【KnowledgeRetriever错误】向量检索出错: {str(e)}", exc_info=True)
            # 返回空列表，避免整个流程失败
            return []
    
    async def check_clarification_needed(self, query: str, kg_context: str = "") -> Tuple[bool, str]:
        """检查是否需要澄清问题
        
        参数:
            query: 查询问题
            kg_context: 知识图谱上下文
            
        返回:
            Tuple[bool, str]: (是否需要澄清, 澄清消息)
        """
        logger.info(f"【KnowledgeRetriever】检查是否需要澄清问题: {query[:50]}...")
        
        if not self.fast_llm:
            logger.warning("【KnowledgeRetriever】无法检查问题澄清: fast_llm不存在")
            return False, ""
        
        try:
            # 检查引擎配置中是否有澄清提示词
            clarification_prompt = None
            if hasattr(self.engine_config, "llm") and hasattr(self.engine_config.llm, "clarifying_question_prompt"):
                logger.info("【KnowledgeRetriever】使用配置中的clarifying_question_prompt")
                clarification_prompt = self.engine_config.llm.clarifying_question_prompt
            else:
                # 使用默认澄清问题提示词
                logger.info("【KnowledgeRetriever】使用默认澄清问题提示词")
                clarification_prompt = """
                你是一个专业的问题分析助手。你的任务是判断问题是否需要进一步澄清。
                
                请根据已知的图谱知识和问题内容，判断问题是否清晰、明确，能够基于已知信息给出满意回答。
                
                图谱知识:
                {graph_knowledges}
                
                今天的日期是：{current_date}
                
                用户的问题是：{question}
                
                请判断这个问题是否需要进一步澄清。如果需要，回答以"Yes,"开头，并说明你需要用户澄清什么。如果不需要，回答"No"。
                """
            
            prompt_template = RichPromptTemplate(template_str=clarification_prompt)
            
            # 预测结果
            logger.info("【KnowledgeRetriever】调用LLM执行问题澄清检查")
            clarification_response = self.fast_llm.predict(
                prompt_template,
                graph_knowledges=kg_context,
                question=query,
                current_date=datetime.now().strftime("%Y-%m-%d")
            )
            
            # 分析响应
            needs_clarification = False
            logger.info(f"【KnowledgeRetriever】澄清检查响应: {clarification_response[:100]}...")
            
            if clarification_response and isinstance(clarification_response, str):
                lower_response = clarification_response.lower()
                if "yes," in lower_response or "yes:" in lower_response:
                    needs_clarification = True
                    logger.info("【KnowledgeRetriever】检测到需要澄清问题")
                    # 提取消息
                    dividers = [":", "?", "because", "as", "since"]
                    for divider in dividers:
                        if divider in clarification_response:
                            parts = clarification_response.split(divider, 1)
                            if len(parts) > 1:
                                clarification_msg = parts[1].strip()
                                logger.info(f"【KnowledgeRetriever】提取到澄清消息: {clarification_msg[:100]}...")
                                return True, clarification_msg
                    
                    return True, clarification_response
            
            logger.info("【KnowledgeRetriever】不需要澄清问题")
            return False, ""
            
        except Exception as e:
            logger.error(f"【KnowledgeRetriever错误】问题澄清检查出错: {str(e)}", exc_info=True)
            return False, ""
    
    async def _run_async(self, func, *args, **kwargs):
        """异步执行同步函数
        
        参数:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        返回:
            Any: 函数执行结果
        """
        logger.debug(f"【KnowledgeRetriever】异步执行函数: {func.__name__}")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs)) 