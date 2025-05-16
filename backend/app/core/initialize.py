import logging
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

from sqlmodel import Session

from app.core.db import get_db_session
from app.tasks.knowledge_graph_tasks import index_database_metadata_to_kg
from app import init_autoflow

logger = logging.getLogger(__name__)

def initialize_database_metadata_kg() -> Optional[str]:
    """
    初始化数据库元数据知识图谱
    
    如果知识图谱不存在，则创建；如果已存在，则验证其完整性
    
    Returns:
        知识图谱存储目录路径或None（如果初始化失败）
    """
    try:
        kg_persist_dir = "./kg_storage/db_metadata"
        
        # 检查知识图谱是否已存在
        if not os.path.exists(kg_persist_dir):
            logger.info("数据库元数据知识图谱不存在，正在创建...")
            os.makedirs(os.path.dirname(kg_persist_dir), exist_ok=True)
            
            # 创建知识图谱
            with get_db_session() as session:
                index_database_metadata_to_kg(persist_dir=kg_persist_dir)
                
            logger.info(f"数据库元数据知识图谱初始化完成，存储路径: {kg_persist_dir}")
        else:
            # 验证知识图谱完整性
            if not os.path.exists(os.path.join(kg_persist_dir, "docstore.json")):
                logger.warning("数据库元数据知识图谱不完整，重新创建...")
                with get_db_session() as session:
                    index_database_metadata_to_kg(persist_dir=kg_persist_dir)
            else:
                logger.info(f"数据库元数据知识图谱已存在，路径: {kg_persist_dir}")
                
        return kg_persist_dir
        
    except Exception as e:
        logger.exception(f"初始化数据库元数据知识图谱失败: {e}")
        return None

def initialize_system():
    """系统初始化入口函数，在应用启动时调用"""
    logger.info("开始系统初始化...")
    
    # 初始化数据库元数据知识图谱
    kg_dir = initialize_database_metadata_kg()
    if kg_dir:
        logger.info(f"数据库元数据知识图谱加载成功: {kg_dir}")
    else:
        logger.warning("数据库元数据知识图谱加载失败")
    
    # 初始化AutoFlow系统
    try:
        with get_db_session() as session:
            init_autoflow(session, None)
        logger.info("AutoFlow系统初始化完成")
    except Exception as e:
        logger.exception(f"初始化AutoFlow系统失败: {e}")
    
    logger.info("系统初始化完成") 