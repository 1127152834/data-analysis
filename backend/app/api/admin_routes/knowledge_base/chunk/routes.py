import logging
import sqlalchemy as sa
from typing import Dict, List, Any

from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep, CurrentSuperuserDep
from app.rag.retrievers.chunk.simple_retriever import (
    ChunkSimpleRetriever,
)
from app.rag.retrievers.chunk.schema import ChunksRetrievalResult
from sqlalchemy.sql import text
from sqlmodel import Session, select

from app.exceptions import InternalServerError, KBNotFound
from .models import KBRetrieveChunksRequest
from app.repositories import knowledge_base_repo
from app.models.chunk import get_kb_chunk_model
from app.repositories.chunk import ChunkRepo
from app.models.knowledge_base_scoped.table_naming import CHUNKS_TABLE_PREFIX

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/admin/knowledge_base/{kb_id}/chunks/retrieve")
def retrieve_chunks(
    db_session: SessionDep,
    user: CurrentSuperuserDep,
    kb_id: int,
    request: KBRetrieveChunksRequest,
) -> ChunksRetrievalResult:
    try:
        vector_search_config = request.retrieval_config.vector_search
        retriever = ChunkSimpleRetriever(
            db_session=db_session,
            knowledge_base_id=kb_id,
            config=vector_search_config,
        )
        return retriever.retrieve_chunks(
            request.query,
        )
    except KBNotFound as e:
        raise e
    except Exception as e:
        logger.exception(e)
        raise InternalServerError()


@router.get("/admin/chunks/by-hash/{chunk_hash}")
def get_chunk_by_hash(
    session: SessionDep,
    user: CurrentSuperuserDep,
    chunk_hash: str,
):
    """
    通过hash获取chunk，使用SQL查询直接在所有知识库表中查找
    
    Args:
        session: 数据库会话
        user: 当前超级用户
        chunk_hash: chunk哈希值
        
    Returns:
        匹配的chunk，如果未找到则抛出404异常
    """
    try:
        # 1. 先查询系统中所有chunks_开头的表
        inspector = sa.inspect(session.bind)
        table_names = inspector.get_table_names()
        
        # 记录所有发现的表名以便调试
        logger.info(f"数据库中的所有表: {table_names}")
        
        # 过滤出所有chunks_开头的表（不区分大小写）
        chunk_tables = [
            name for name in table_names 
            if name.lower().startswith(CHUNKS_TABLE_PREFIX.lower())
        ]
        
        logger.info(f"将要查询的chunk表: {chunk_tables}")
        logger.info(f"查询的hash值: {chunk_hash}")
        
        # 2. 构建一个查询数组，检查每个表中是否有匹配哈希的chunk
        result = None
        kb_id = None
        
        for table_name in chunk_tables:
            # 从表名提取知识库ID
            try:
                current_kb_id = int(table_name.replace(CHUNKS_TABLE_PREFIX, ""))
                
                # 执行原生SQL查询
                query = text(f"SELECT * FROM {table_name} WHERE hash = :hash LIMIT 1")
                query_result = session.execute(query, {"hash": chunk_hash}).first()
                
                if query_result:
                    # 记录找到结果的表
                    logger.info(f"在表 {table_name} 中找到匹配的chunk")
                    
                    kb_id = current_kb_id
                    result = dict(query_result._mapping)
                    break
            except (ValueError, Exception) as e:
                logger.warning(f"处理表 {table_name} 时出错: {e}")
                continue
        
        # 3. 如果找到结果，使用对应知识库的Chunk模型格式化它
        if result and kb_id:
            kb = knowledge_base_repo.get(session, kb_id)
            if kb:
                # 获取正确的chunk模型
                chunk_model = get_kb_chunk_model(kb)
                # 此处只需返回原始结果，FastAPI会处理序列化
                return result
                
        # 如果所有知识库都没找到，返回404
        logger.error(f"在所有表中都未找到哈希值为 {chunk_hash} 的chunk")
        raise HTTPException(
            status_code=404,
            detail=f"找不到哈希值为 {chunk_hash} 的chunk",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(e)
        raise InternalServerError()
