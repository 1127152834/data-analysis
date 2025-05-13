import logging
import re
import sqlalchemy as sa
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.api import deps
from app.api.deps import SessionDep
from app.repositories.chunk_repo import ChunkRepo
from app.schemas import ChunkContent
from sqlalchemy.sql import text
from app.models.knowledge_base_scoped.table_naming import CHUNKS_TABLE_PREFIX

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chunks/id/{chunk_id}", response_model=ChunkContent)
def get_chunk_by_id(chunk_id: str, db: SessionDep):
    """
    根据Chunk ID获取chunk内容
    """
    logger.info(f"正在查询ID为 {chunk_id} 的chunk")

    try:
        # 尝试调用repo获取chunk
        chunk_repo = ChunkRepo(db)
        chunk = chunk_repo.get_chunk_by_id(chunk_id)

        if not chunk:
            logger.warning(f"找不到ID为 {chunk_id} 的chunk")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"找不到ID为 {chunk_id} 的chunk",
            )

        return {"content": chunk.text}
    except ValueError as e:
        logger.error(f"查询chunk时出现值错误: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"参数错误: {str(e)}"
        )
    except Exception as e:
        logger.error(f"查询chunk时出现异常: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}",
        )
