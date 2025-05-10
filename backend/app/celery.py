from celery import Celery  # 导入Celery异步任务框架

from app.core.config import settings  # 导入应用配置


# 创建Celery应用实例
app = Celery(
    settings.PROJECT_NAME,  # 设置应用名称
    broker=settings.CELERY_BROKER_URL,  # 设置消息代理URL
    backend=settings.CELERY_RESULT_BACKEND,  # 设置结果后端URL
)

# 更新Celery配置
app.conf.update(
    task_acks_late=True,  # 任务执行完成后再确认，可以防止任务丢失
    task_reject_on_worker_lost=True,  # 如果工作进程丢失，拒绝任务并重新放入队列
    task_routes=[
        {
            "app.tasks.evaluate.*": {"queue": "evaluation"}
        },  # 评估任务路由到evaluation队列
        {"*": {"queue": "default"}},  # 其他任务路由到default队列
    ],
    broker_connection_retry_on_startup=True,  # 启动时尝试重新连接消息代理
)

# 自动发现tasks模块中的任务
app.autodiscover_tasks(["app"])
