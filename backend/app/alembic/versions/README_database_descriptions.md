# 数据库问答功能 - 数据库描述字段迁移

## 功能概述

为了支持数据库问答功能，本次迁移向 `DatabaseConnection` 模型添加了三个新字段：

1. **description_for_llm** - 用于LLM的业务场景描述
2. **table_descriptions** - 表级别的描述信息 (JSON格式)
3. **column_descriptions** - 列级别的描述信息 (JSON格式)

这些字段将使AI能够理解数据库的业务含义，生成更加准确的SQL查询，并提供更好的问答体验。

## 迁移文件

`add_database_descriptions.py` 迁移文件完成以下操作：

1. 添加 `description_for_llm` 字符串字段(最大长度1024字符)
2. 添加 `table_descriptions` JSON字段，用于存储表描述
3. 添加 `column_descriptions` JSON字段，用于存储列描述
4. 创建 `description_for_llm` 字段的索引以优化查询

## 数据格式定义

### table_descriptions (表描述)

表描述使用简单的键值对格式：

```json
{
  "users": "用户信息表，存储系统用户的基本信息",
  "orders": "订单表，记录所有交易订单数据",
  "products": "产品表，包含所有可销售产品的详细信息"
}
```

### column_descriptions (列描述)

列描述使用嵌套的键值对格式：

```json
{
  "users": {
    "id": "用户唯一标识",
    "name": "用户姓名",
    "email": "用户电子邮箱，用于登录和通知"
  },
  "orders": {
    "id": "订单唯一标识",
    "user_id": "下单用户ID，关联到users表",
    "total_amount": "订单总金额，单位为元"
  }
}
```

## 应用影响

1. **模型修改**：`DatabaseConnection` 模型增加了新字段
2. **参数类扩展**：`DatabaseConnectionCreate` 和 `DatabaseConnectionUpdate` 参数类增加了对应字段
3. **API扩展**：相关API将支持读取和更新这些描述字段
4. **前端界面**：需要新增界面组件支持这些描述的管理

## 回滚说明

如需回滚，迁移脚本的 `downgrade()` 函数会：

1. 删除 `description_for_llm` 字段的索引
2. 删除所有新增字段

请注意：回滚将导致已保存的所有数据库描述信息丢失。

## 相关任务

本迁移是实现数据库问答功能的第一步，后续还需完成：

1. 修改数据库连接表单，支持编辑业务描述
2. 实现表/列描述的批量管理功能 
3. 集成到聊天引擎，支持基于描述的SQL生成 