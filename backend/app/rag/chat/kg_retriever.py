import logging
from typing import List, Dict, Any, Optional

from llama_index.core import KnowledgeGraphIndex, QueryBundle
from llama_index.core.indices.query.base import BaseQueryEngine
from llama_index.core.retrievers import KGTableRetriever
from llama_index.core.response.schema import NodeWithScore
from llama_index.core.schema import QueryType, QueryMode

logger = logging.getLogger(__name__)

class DatabaseMetadataKGRetriever:
    """数据库元数据知识图谱检索器，用于帮助LLM理解数据库结构和关系"""
    
    def __init__(
        self, 
        kg_index: KnowledgeGraphIndex,
        relevance_threshold: float = 0.7,
        max_relations: int = 3,
        max_results: int = 10,
    ):
        self.kg_index = kg_index
        self.relevance_threshold = relevance_threshold
        self.max_relations = max_relations
        self.max_results = max_results
        self.query_engine = kg_index.as_query_engine(
            include_text=True,
            response_mode="no_text",
            max_paths=max_relations
        )
    
    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        检索与查询相关的数据库元数据
        
        Args:
            query: 用户查询
            
        Returns:
            结构化的数据库元数据列表
        """
        logger.info(f"从知识图谱检索与查询相关的数据库元数据: '{query}'")
        try:
            # 使用KG查询引擎检索相关信息
            response = self.query_engine.query(query)
            
            # 提取检索到的三元组
            all_metadata = []
            if hasattr(response, "source_nodes") and response.source_nodes:
                for node in response.source_nodes:
                    # 提取三元组
                    if hasattr(node, "metadata") and "triplet" in node.metadata:
                        triplet = node.metadata["triplet"]
                        if isinstance(triplet, tuple) and len(triplet) == 3:
                            subject, relation, object_text = triplet
                            all_metadata.append({
                                "subject": subject,
                                "relation": relation,
                                "object": object_text,
                                "score": node.score if hasattr(node, "score") else 1.0
                            })
            
            # 按相关性排序并筛选
            all_metadata.sort(key=lambda x: x.get("score", 0), reverse=True)
            filtered_metadata = [
                item for item in all_metadata 
                if item.get("score", 0) >= self.relevance_threshold
            ][:self.max_results]
            
            logger.info(f"检索到{len(filtered_metadata)}条相关数据库元数据")
            return filtered_metadata
            
        except Exception as e:
            logger.exception(f"从知识图谱检索数据库元数据时出错: {e}")
            return []
    
    def retrieve_db_structure(self, database_name: Optional[str] = None) -> Dict[str, Any]:
        """
        检索数据库结构信息，可以指定特定数据库或检索所有数据库
        
        Args:
            database_name: 可选，特定数据库名称
            
        Returns:
            数据库结构的字典表示
        """
        try:
            # 构建结构化的数据库信息
            structure = {}
            
            # 如果指定了数据库名称，只检索该数据库的信息
            if database_name:
                # 检索数据库基本信息
                db_info = self._retrieve_entity_info(database_name)
                if not db_info:
                    return {}
                
                # 检索表信息
                tables = self._retrieve_related_entities(database_name, "contains_table")
                db_info["tables"] = {}
                
                # 检索每个表的列信息
                for table in tables:
                    table_name = table["object"]
                    table_info = self._retrieve_entity_info(table_name)
                    columns = self._retrieve_related_entities(table_name, "contains_column")
                    table_info["columns"] = {
                        col["object"].split(".")[-1]: {
                            "description": self._get_entity_description(col["object"])
                        } for col in columns
                    }
                    db_info["tables"][table_name.split(".")[-1]] = table_info
                
                structure[database_name] = db_info
            else:
                # 检索所有数据库
                databases = self._retrieve_entities_by_type("Database")
                for db in databases:
                    db_name = db["subject"]
                    structure[db_name] = self.retrieve_db_structure(db_name)[db_name]
            
            return structure
        
        except Exception as e:
            logger.exception(f"检索数据库结构时出错: {e}")
            return {}
    
    def _retrieve_entity_info(self, entity_name: str) -> Dict[str, Any]:
        """检索实体的基本信息"""
        entity_info = {"name": entity_name.split(".")[-1]}
        
        # 获取实体类型
        type_info = self._retrieve_related_entities(entity_name, "is_a", reverse=False)
        if type_info:
            entity_info["type"] = type_info[0]["object"]
        
        # 获取实体描述
        description = self._get_entity_description(entity_name)
        if description:
            entity_info["description"] = description
            
        return entity_info
    
    def _get_entity_description(self, entity_name: str) -> str:
        """获取实体的描述"""
        desc_info = self._retrieve_related_entities(entity_name, "has_description", reverse=False)
        if desc_info:
            return desc_info[0]["object"]
        return ""
    
    def _retrieve_related_entities(self, entity_name: str, relation: str, reverse: bool = False) -> List[Dict[str, Any]]:
        """检索与实体有特定关系的其他实体"""
        triplets = []
        
        # 构建KG检索查询
        query_str = f"查找与{entity_name}通过{relation}关系连接的实体"
        
        try:
            # 执行图查询
            if reverse:
                # 反向查询：entity_name作为object
                retriever = KGTableRetriever(
                    self.kg_index,
                    include_text=False,
                    object_limit=15,
                    relation=relation,
                    object_node_text=entity_name
                )
            else:
                # 正向查询：entity_name作为subject
                retriever = KGTableRetriever(
                    self.kg_index,
                    include_text=False,
                    object_limit=15,
                    subject_node_text=entity_name,
                    relation=relation
                )
                
            nodes = retriever.retrieve(query_str)
            
            # 处理结果
            for node in nodes:
                if "triplet" in node.metadata:
                    subject, rel, obj = node.metadata["triplet"]
                    triplets.append({
                        "subject": subject,
                        "relation": rel,
                        "object": obj
                    })
                    
            return triplets
        except Exception as e:
            logger.error(f"检索相关实体时出错: {e}")
            return []
    
    def _retrieve_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """根据类型检索实体"""
        try:
            retriever = KGTableRetriever(
                self.kg_index,
                include_text=False,
                object_limit=50,
                relation="is_a",
                object_node_text=entity_type
            )
            
            nodes = retriever.retrieve(f"查找所有{entity_type}类型的实体")
            
            return [
                {"subject": node.metadata["triplet"][0], "type": entity_type}
                for node in nodes if "triplet" in node.metadata
            ]
        except Exception as e:
            logger.error(f"根据类型检索实体时出错: {e}")
            return [] 