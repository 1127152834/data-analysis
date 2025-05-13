from celery import Celery, Task
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.tasks.knowledge_graph_tasks import update_database_metadata_kg

# 设置日志记录器
logger = logging.getLogger(__name__)

# 创建Celery应用
celery_app = Celery("autoflow_tasks")

# 配置Celery
celery_app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/1",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1小时超时
    worker_max_tasks_per_child=100,
    worker_prefetch_multiplier=4,
)

# 定义定期任务
celery_app.conf.beat_schedule = {
    "update-database-metadata-kg-daily": {
        "task": "app.tasks.celery_tasks.update_database_metadata_kg_task",
        "schedule": timedelta(days=1),  # 每天执行一次
        "options": {"queue": "kg_tasks"},
    },
}

class LoggingTask(Task):
    """扩展Task以添加更多日志记录和错误处理"""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """任务失败时的处理函数"""
        logger.error(
            f"任务 {self.name} 失败 (id: {task_id}): {exc}\n参数: {args}, {kwargs}\n{einfo}"
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)
        
    def on_success(self, retval, task_id, args, kwargs):
        """任务成功时的处理函数"""
        logger.info(
            f"任务 {self.name} 成功 (id: {task_id})\n参数: {args}, {kwargs}\n返回值: {retval}"
        )
        super().on_success(retval, task_id, args, kwargs)
        
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """任务重试时的处理函数"""
        logger.warning(
            f"任务 {self.name} 重试 (id: {task_id}): {exc}\n参数: {args}, {kwargs}\n{einfo}"
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)

@celery_app.task(base=LoggingTask, bind=True, name="app.tasks.celery_tasks.update_database_metadata_kg_task")
def update_database_metadata_kg_task(self) -> Dict[str, Any]:
    """
    定期更新数据库元数据知识图谱任务
    
    将所有活跃的数据库连接的元数据（表结构、列信息等）转换为三元组形式并更新到知识图谱中
    """
    logger.info("开始执行数据库元数据知识图谱更新任务")
    
    try:
        start_time = datetime.now()
        
        # 调用知识图谱更新函数
        update_database_metadata_kg()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "status": "success",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "message": "数据库元数据知识图谱更新成功"
        }
        
        logger.info(f"数据库元数据知识图谱更新任务完成，耗时: {duration}秒")
        return result
        
    except Exception as e:
        logger.exception(f"数据库元数据知识图谱更新任务失败: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "message": "数据库元数据知识图谱更新失败"
        } 