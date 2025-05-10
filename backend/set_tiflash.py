from sqlalchemy import create_engine, text
from app.core.config import settings

# 创建数据库连接
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

# 为chunks_1表设置TiFlash副本
with engine.connect() as conn:
    conn.execute(text("ALTER TABLE chunks_1 SET TIFLASH REPLICA 1"))
    conn.commit()
    print("已为chunks_1表设置TiFlash副本")

    # 检查同步状态
    result = conn.execute(
        text(
            'SELECT * FROM information_schema.tiflash_replica WHERE TABLE_SCHEMA = "test" AND TABLE_NAME = "chunks_1"'
        )
    )
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"表: {row[1]}, 副本数: {row[3]}, 可用: {row[5]}, 进度: {row[6]}")
    else:
        print("未找到TiFlash副本信息，请稍后再查询")
