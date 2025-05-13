import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from sqlmodel import Session
from llama_index.core import KnowledgeGraphIndex, StorageContext
from llama_index.graph_stores.simple import SimpleGraphStore

from app.core.database import get_session
from app.models.database_connection import DatabaseConnection
from app.repositories import database_connection_repo

logger = logging.getLogger(__name__)

def generate_triplets_for_db_connection(db_conn: DatabaseConnection) -> List[Tuple[str, str, str]]:
    """从数据库连接生成知识图谱三元组"""
    triplets = []
    
    # 数据库基本信息
    triplets.append((db_conn.name, "is_a", "Database"))
    triplets.append((db_conn.name, "has_type", db_conn.database_type.value))
    
    if db_conn.description_for_llm:
        triplets.append((db_conn.name, "has_description", db_conn.description_for_llm))
        
    # 表信息
    for table_name, table_desc in db_conn.table_descriptions.items():
        qualified_table_name = f"{db_conn.name}.{table_name}"
        triplets.append((db_conn.name, "contains_table", qualified_table_name))
        triplets.append((qualified_table_name, "is_a", "Table"))
        triplets.append((qualified_table_name, "has_description", table_desc))
        
        # 列信息
        if db_conn.column_descriptions and table_name in db_conn.column_descriptions:
            for col_name, col_desc in db_conn.column_descriptions[table_name].items():
                qualified_col_name = f"{qualified_table_name}.{col_name}"
                triplets.append((qualified_table_name, "contains_column", qualified_col_name))
                triplets.append((qualified_col_name, "is_a", "Column"))
                triplets.append((qualified_col_name, "has_description", col_desc))
    
    return triplets

def index_database_metadata_to_kg(persist_dir: Optional[str] = "./kg_storage/db_metadata"):
    """将所有数据库连接的元数据索引到知识图谱中"""
    try:
        # 初始化图存储
        graph_store = SimpleGraphStore()
        storage_context = StorageContext.from_defaults(graph_store=graph_store)
        
        # 创建知识图谱索引
        kg_index = KnowledgeGraphIndex(
            [],  # 空节点列表，稍后添加三元组
            storage_context=storage_context,
            index_id="db_metadata_kg"
        )
        
        # 获取所有活跃的数据库连接
        with get_session() as session:
            db_connections = database_connection_repo.get_all_active(session)
            
        total_triplets = 0
        
        # 为每个数据库连接生成并添加三元组
        for db_conn in db_connections:
            try:
                triplets = generate_triplets_for_db_connection(db_conn)
                for subj, rel, obj in triplets:
                    kg_index.upsert_triplet((subj, rel, obj))
                total_triplets += len(triplets)
                logger.info(f"已为数据库'{db_conn.name}'添加{len(triplets)}个三元组")
            except Exception as e:
                logger.error(f"处理数据库'{db_conn.name}'时出错: {e}")
        
        # 持久化知识图谱
        if persist_dir:
            kg_index.storage_context.persist(persist_dir=persist_dir)
            logger.info(f"知识图谱已持久化到{persist_dir}")
        
        logger.info(f"数据库元数据知识图谱索引完成，共添加{total_triplets}个三元组")
        return kg_index
    
    except Exception as e:
        logger.exception(f"创建数据库元数据知识图谱失败: {e}")
        raise

# 可以被Celery任务调用的函数
def update_database_metadata_kg():
    """更新数据库元数据知识图谱（可作为定期任务运行）"""
    logger.info("开始更新数据库元数据知识图谱")
    index_database_metadata_to_kg()
    logger.info("数据库元数据知识图谱更新完成") 