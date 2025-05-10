from sqlalchemy import create_engine, text
from app.core.config import settings

# 创建数据库连接
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))

# 尝试创建向量索引
try:
    with engine.connect() as conn:
        query = text(
            "ALTER TABLE chunks_1 ADD VECTOR INDEX vec_idx_embedding ((VEC_COSINE_DISTANCE(embedding)))"
        )
        conn.execute(query)
        conn.commit()
        print("成功创建向量索引")
except Exception as e:
    print(f"错误: {e}")
