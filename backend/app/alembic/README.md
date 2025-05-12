# 数据库迁移管理模块

## 模块概述
本模块使用Alembic进行数据库版本控制，管理SQLModel模型与数据库Schema的同步变更。主要功能包括：
- 数据库版本历史管理
- Schema变更脚本生成/执行
- 多环境迁移配置
- 向量类型(TiDB Vector)支持

## 核心文件结构
```
alembic/
├── env.py            # 迁移环境主配置
├── script.py.mako    # 迁移脚本模板
└── versions/         # 迁移历史脚本
```

## 关键功能解析

### 1. 环境配置 (env.py)
```python
# 动态获取数据库配置
def get_url():
    return str(settings.SQLALCHEMY_DATABASE_URI)

# 过滤知识库动态表
def include_name(name, type_, parent_names):
    return not any([
        KB_CHUNKS_TABLE_PATTERN.match(name),
        KB_ENTITIES_TABLE_PATTERN.match(name),
        KB_RELATIONSHIPS_TABLE_PATTERN.match(name)
    ])
```

### 2. 迁移脚本管理
- 版本号格式：`<版本hash>_<描述>.py`
- 典型操作示例：
  ```python
  # 修改字段类型
  op.alter_column('llms', 'provider', type_=sa.String(32))
  
  # 添加新表
  op.create_table('evaluation_datasets', ...)
  
  # 执行数据迁移
  op.execute("UPDATE models SET provider = lower(provider)")
  ```

## 编码规范
1. **版本命名**：采用12位hash前缀+功能描述
2. **事务管理**：使用`with context.begin_transaction()`
3. **类型变更**：保留原始类型信息用于回滚
4. **数据迁移**：与Schema变更分离处理
5. **向量支持**：集成TiDB Vector类型
   ```python
   connection.dialect.ischema_names["vector"] = VectorType
   ```

## 开发指南
```bash
# 创建新迁移
alembic revision -m "add_feature_table"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 生成迁移脚本
alembic revision --autogenerate -m "description"
```

> **注意**：动态表（知识库相关）会被自动排除在迁移检测之外，需单独处理其Schema变更
```

这个README结构包含：
1. 模块定位和核心功能
2. 关键代码解析
3. 编码规范总结
4. 常用开发命令
5. 特殊处理说明（动态表过滤）