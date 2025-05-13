import json
import logging
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
from datetime import datetime

from llama_index.core.llms import LLM

from app.rag.chat.config import (
    DatabaseOption, 
    LinkedDatabaseConfig,
    DatabaseRoutingStrategy
)
from app.models import DatabaseConnection
from app.repositories.database_connection import DatabaseConnectionRepo

# 配置日志记录器
logger = logging.getLogger("database_router")

class DatabaseRouter:
    """
    数据库路由器
    
    基于用户问题和数据库描述，决定使用哪个或哪些数据库执行查询
    支持多种路由策略和LLM辅助决策
    """
    
    def __init__(
        self,
        db_option: DatabaseOption,
        db_session: Any,
        llm: Optional[LLM] = None
    ):
        """
        初始化数据库路由器
        
        Args:
            db_option: 数据库选项配置
            db_session: 数据库会话对象
            llm: 语言模型（用于LLM辅助路由决策）
        """
        self.db_option = db_option
        self.db_session = db_session
        self.llm = llm
        self.repo = DatabaseConnectionRepo()
        self._embeddings_cache = {}  # 数据库描述的向量缓存

    def get_relevant_databases(
        self, 
        question: str,
        user_id: str = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[LinkedDatabaseConfig, float]]:
        """
        获取与用户问题相关的数据库配置
        
        Args:
            question: 用户问题
            user_id: 用户ID（用于权限检查）
            context: 上下文信息（可能包含历史对话等）
            
        Returns:
            List[Tuple[LinkedDatabaseConfig, float]]: 相关数据库配置及其相关性分数的列表
        """
        # 获取所有启用的数据库配置
        all_db_configs = [
            config for config in self.db_option.linked_database_configs
            if config.enabled
        ]
        
        # 如果没有可用的数据库，返回空列表
        if not all_db_configs:
            logger.warning("没有可用的数据库配置")
            return []
            
        # 如果路由策略是MANUAL且上下文包含指定的数据库ID
        if (self.db_option.routing_strategy == DatabaseRoutingStrategy.MANUAL 
                and context and 'specified_database_id' in context):
            db_id = context['specified_database_id']
            for config in all_db_configs:
                if config.id == db_id:
                    return [(config, 1.0)]  # 返回指定的数据库，分数为1.0
            logger.warning(f"指定的数据库ID {db_id} 不存在或未启用")
            return []
            
        # 根据路由策略选择不同的评分方法
        if self.db_option.use_llm_for_routing and self.llm:
            # 使用LLM进行路由决策
            return self._route_with_llm(question, all_db_configs, user_id)
        else:
            # 使用向量相似度或基于标签匹配进行路由决策
            return self._route_with_similarity(question, all_db_configs, user_id, context)
            
    def _route_with_similarity(
        self,
        question: str,
        all_db_configs: List[LinkedDatabaseConfig],
        user_id: str = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[LinkedDatabaseConfig, float]]:
        """
        使用相似度计算进行路由决策
        
        Args:
            question: 用户问题
            all_db_configs: 所有可用的数据库配置
            user_id: 用户ID
            context: 上下文信息
            
        Returns:
            List[Tuple[LinkedDatabaseConfig, float]]: 相关数据库配置及其相关性分数的列表
        """
        db_scores = []
        
        # 获取所有数据库的业务描述
        for config in all_db_configs:
            # 获取数据库连接
            db_connection = self._get_db_connection(config.id)
            if not db_connection:
                continue
                
            # 计算相关性分数
            score = self._calculate_relevance_score(question, config, db_connection, context)
            
            # 应用路由权重调整
            score *= config.routing_weight
            
            # 主要数据库可以获得额外加分
            if config.is_primary:
                score += 0.1  # 加0.1分，确保在其他条件相同的情况下，主数据库更可能被选中
                
            db_scores.append((config, score))
            
        # 按分数从高到低排序
        db_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 根据路由策略筛选数据库
        threshold = self.db_option.routing_score_threshold
        
        if self.db_option.routing_strategy == DatabaseRoutingStrategy.SINGLE_BEST:
            # 只返回得分最高的一个数据库（如果其分数高于阈值）
            if db_scores and db_scores[0][1] >= threshold:
                return [db_scores[0]]
                
        elif self.db_option.routing_strategy == DatabaseRoutingStrategy.TOP_N:
            # 返回得分最高的N个数据库（如果其分数高于阈值）
            top_n = min(self.db_option.routing_top_n, len(db_scores))
            result = []
            for i in range(top_n):
                if i < len(db_scores) and db_scores[i][1] >= threshold:
                    result.append(db_scores[i])
            return result
            
        elif self.db_option.routing_strategy == DatabaseRoutingStrategy.ALL_QUALIFIED:
            # 返回所有得分高于阈值的数据库
            return [db for db in db_scores if db[1] >= threshold]
            
        elif self.db_option.routing_strategy == DatabaseRoutingStrategy.CONTEXTUAL:
            # 基于上下文的复杂路由逻辑
            if context and 'chat_history' in context:
                # 考虑最近对话历史中提到的数据库关键词
                # 这里可以实现更复杂的上下文感知逻辑
                return [db for db in db_scores if db[1] >= threshold]
            else:
                # 如果没有历史上下文，退化为ALL_QUALIFIED策略
                return [db for db in db_scores if db[1] >= threshold]
                
        # 如果没有满足条件的数据库，应用回退策略
        if not db_scores:
            return []
            
        # 应用回退策略
        if self.db_option.fallback_strategy == "primary":
            # 查找主数据库
            for config, score in db_scores:
                if config.is_primary:
                    return [(config, max(score, threshold))]  # 确保分数至少为阈值
                    
        elif self.db_option.fallback_strategy == "any":
            # 使用任意一个数据库（通常是第一个）
            return [db_scores[0]]
            
        # 默认情况下返回空列表
        return []
        
    def _route_with_llm(
        self,
        question: str,
        all_db_configs: List[LinkedDatabaseConfig],
        user_id: str = None
    ) -> List[Tuple[LinkedDatabaseConfig, float]]:
        """
        使用LLM进行路由决策
        
        Args:
            question: 用户问题
            all_db_configs: 所有可用的数据库配置
            user_id: 用户ID
            
        Returns:
            List[Tuple[LinkedDatabaseConfig, float]]: 相关数据库配置及其相关性分数的列表
        """
        if not self.llm:
            logger.warning("未提供LLM，无法使用LLM进行路由决策")
            return self._route_with_similarity(question, all_db_configs, user_id)
            
        # 构建数据库描述
        db_descriptions = ""
        id_to_config = {}
        
        for config in all_db_configs:
            db_connection = self._get_db_connection(config.id)
            if not db_connection:
                continue
                
            # 使用覆盖描述或数据库原始描述
            description = config.business_description_override or db_connection.description_for_llm or ""
            if not description:
                description = f"数据库 {db_connection.name}，类型: {db_connection.type}"
                
            # 如果有表描述信息，可以添加到描述中
            if hasattr(db_connection, 'table_descriptions') and db_connection.table_descriptions:
                table_info = "\n包含的主要表: " + ", ".join(db_connection.table_descriptions.keys())
                description += table_info
                
            db_descriptions += f"数据库ID {config.id}: {description}\n\n"
            id_to_config[str(config.id)] = config
            
        # 构建LLM提示词
        prompt = self.db_option.llm_routing_prompt_template.format(
            question=question,
            database_descriptions=db_descriptions
        )
        
        try:
            # 调用LLM进行路由决策
            response = self.llm.complete(prompt)
            response_text = response.text
            
            # 尝试解析JSON响应
            try:
                # 查找JSON部分
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    result = json.loads(json_str)
                    
                    # 提取分数
                    if 'scores' in result and isinstance(result['scores'], dict):
                        scores = result['scores']
                        
                        # 记录推理过程
                        if 'reasoning' in result:
                            logger.info(f"LLM路由推理: {result['reasoning']}")
                            
                        # 构建结果列表
                        db_scores = []
                        for db_id, score in scores.items():
                            if db_id in id_to_config:
                                db_scores.append((id_to_config[db_id], float(score)))
                                
                        # 按分数从高到低排序
                        db_scores.sort(key=lambda x: x[1], reverse=True)
                        
                        # 应用路由策略
                        threshold = self.db_option.routing_score_threshold
                        
                        if self.db_option.routing_strategy == DatabaseRoutingStrategy.SINGLE_BEST:
                            if db_scores and db_scores[0][1] >= threshold:
                                return [db_scores[0]]
                                
                        elif self.db_option.routing_strategy == DatabaseRoutingStrategy.TOP_N:
                            top_n = min(self.db_option.routing_top_n, len(db_scores))
                            result = []
                            for i in range(top_n):
                                if i < len(db_scores) and db_scores[i][1] >= threshold:
                                    result.append(db_scores[i])
                            return result
                            
                        elif self.db_option.routing_strategy == DatabaseRoutingStrategy.ALL_QUALIFIED:
                            return [db for db in db_scores if db[1] >= threshold]
                            
                        # 应用回退策略
                        if self.db_option.fallback_strategy == "primary":
                            for config, score in db_scores:
                                if config.is_primary:
                                    return [(config, max(score, threshold))]
                                    
                        elif self.db_option.fallback_strategy == "any":
                            return [db_scores[0]]
                            
                        return []
            except Exception as e:
                logger.error(f"解析LLM路由响应失败: {str(e)}")
                
        except Exception as e:
            logger.error(f"LLM路由决策失败: {str(e)}")
            
        # 如果LLM路由失败，回退到相似度路由
        logger.info("LLM路由失败，回退到相似度路由")
        return self._route_with_similarity(question, all_db_configs, user_id)
        
    def _calculate_relevance_score(
        self,
        question: str,
        db_config: LinkedDatabaseConfig,
        db_connection: DatabaseConnection,
        context: Optional[Dict[str, Any]] = None
    ) -> float:
        """
        计算问题与数据库的相关性分数
        
        Args:
            question: 用户问题
            db_config: 数据库配置
            db_connection: 数据库连接
            context: 上下文信息
            
        Returns:
            float: 相关性分数，范围0.0-1.0
        """
        # 初始分数
        score = 0.5  # 基础分数
        
        # 获取业务描述
        business_desc = db_config.business_description_override or db_connection.description_for_llm or ""
        
        if not business_desc:
            return score  # 如果没有描述，返回基础分数
            
        # 简单的关键词匹配
        desc_lower = business_desc.lower()
        question_lower = question.lower()
        
        # 词袋模型计算相似度
        desc_words = set(desc_lower.split())
        question_words = set(question_lower.split())
        
        # 计算交集大小
        common_words = desc_words.intersection(question_words)
        
        # 计算Jaccard相似度
        if len(desc_words) > 0 and len(question_words) > 0:
            jaccard_sim = len(common_words) / len(desc_words.union(question_words))
            score += jaccard_sim * 0.3  # 加权影响
            
        # 检查业务标签匹配
        if db_config.business_tags:
            for tag in db_config.business_tags:
                if tag.lower() in question_lower:
                    score += 0.15  # 每个匹配的标签增加分数
                    
        # 考虑上下文中的历史查询
        if context and 'chat_history' in context:
            # 这里可以实现更复杂的上下文相似度计算
            # 例如，如果最近成功查询过该数据库，可以增加分数
            pass
            
        # 确保分数在0.0-1.0范围内
        return max(0.0, min(1.0, score))
        
    def _get_db_connection(self, db_id: int) -> Optional[DatabaseConnection]:
        """
        获取数据库连接对象
        
        Args:
            db_id: 数据库ID
            
        Returns:
            Optional[DatabaseConnection]: 数据库连接对象，如果不存在则返回None
        """
        try:
            return self.repo.get_by_id(self.db_session, db_id)
        except Exception as e:
            logger.error(f"获取数据库连接失败, ID: {db_id}, 错误: {str(e)}")
            return None 