import os
import time
from typing import List, IO, Generator
from fastapi import APIRouter, UploadFile, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep, CurrentSuperuserDep
from app.file_storage import default_file_storage
from app.utils.uuid6 import uuid7
from app.site_settings import SiteSetting
from app.core.config import settings

router = APIRouter()

# 支持的图片格式
SUPPORTED_IMAGE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

@router.post("/admin/images/upload")
def upload_images(
    user: CurrentSuperuserDep, files: List[UploadFile]
) -> List[dict]:
    """
    上传图片文件到static/images目录
    
    参数:
    - user: 当前登录的超级用户
    - files: 要上传的图片文件列表
    
    返回:
    - 上传成功的图片URL列表
    """
    results = []
    for file in files:
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文件名不能为空",
            )
        
        sys_max_upload_file_size = SiteSetting.max_upload_file_size
        if file.size > sys_max_upload_file_size:
            upload_file_size_in_mb = file.size / 1024 / 1024
            max_upload_file_size_in_mb = sys_max_upload_file_size / 1024 / 1024
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="上传文件大小 ({:.2f} MiB) 超过最大允许大小 ({:.2f} MiB)".format(
                    upload_file_size_in_mb, max_upload_file_size_in_mb
                ),
            )

        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的图片格式 {file_ext}。支持的格式: {', '.join(SUPPORTED_IMAGE_TYPES.keys())}",
            )
        
        # 安全的文件名处理
        safe_filename = f"{int(time.time())}-{uuid7().hex}{file_ext}"
        file_path = f"static/images/{safe_filename}"
        
        # 保存文件
        default_file_storage.save(file_path, file.file)
        
        # 构建可访问的URL
        file_url = f"/api/v1/images/{safe_filename}"
        
        results.append({
            "name": file.filename,
            "size": default_file_storage.size(file_path),
            "path": file_path,
            "url": file_url,
            "mime_type": SUPPORTED_IMAGE_TYPES[file_ext],
        })
    
    return results

@router.get("/images/{image_name}")
def get_image(image_name: str):
    """
    获取静态图片
    
    参数:
    - image_name: 图片文件名
    
    返回:
    - 图片文件
    """
    file_path = f"static/images/{image_name}"
    file_ext = os.path.splitext(image_name)[1].lower()
    
    if not default_file_storage.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="图片不存在",
        )
    
    if file_ext not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片格式",
        )
    
    def iterfile() -> Generator[bytes, None, None]:
        with default_file_storage.open(file_path, "rb") as f:
            yield from f
    
    return StreamingResponse(
        iterfile(),
        media_type=SUPPORTED_IMAGE_TYPES[file_ext]
    ) 