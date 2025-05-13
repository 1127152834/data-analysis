#!/usr/bin/env python
"""
获取数据库中所有表的结构信息并生成创建语句
"""
from app.core.db import engine
from sqlalchemy import inspect, MetaData
import json

def get_column_type_str(column):
    """将SQLAlchemy列类型转换为字符串表示"""
    ctype = str(column['type'])
    return ctype

def main():
    inspector = inspect(engine)
    
    # 获取所有表名
    table_names = inspector.get_table_names()
    print(f"数据库中共有 {len(table_names)} 个表")
    
    schema_info = {}
    
    for table_name in sorted(table_names):
        print(f"\n处理表 {table_name}...")
        
        # 获取表信息
        columns = inspector.get_columns(table_name)
        primary_keys = inspector.get_pk_constraint(table_name).get('constrained_columns', [])
        foreign_keys = inspector.get_foreign_keys(table_name)
        indexes = inspector.get_indexes(table_name)
        
        # 构建表结构信息
        table_info = {
            'columns': [],
            'primary_keys': primary_keys,
            'foreign_keys': [],
            'indexes': []
        }
        
        # 处理列信息
        for column in columns:
            col_info = {
                'name': column['name'],
                'type': get_column_type_str(column),
                'nullable': column['nullable'],
                'default': str(column['default']) if column.get('default') else None,
                'primary_key': column['name'] in primary_keys,
                'autoincrement': column.get('autoincrement', False)
            }
            table_info['columns'].append(col_info)
        
        # 处理外键信息
        for fk in foreign_keys:
            fk_info = {
                'constrained_columns': fk['constrained_columns'],
                'referred_table': fk['referred_table'],
                'referred_columns': fk['referred_columns']
            }
            table_info['foreign_keys'].append(fk_info)
        
        # 处理索引信息
        for idx in indexes:
            idx_info = {
                'name': idx['name'],
                'columns': idx['column_names'],
                'unique': idx['unique']
            }
            table_info['indexes'].append(idx_info)
        
        schema_info[table_name] = table_info
        
        # 打印表结构摘要
        print(f"  列数: {len(columns)}")
        print(f"  主键: {primary_keys}")
        print(f"  外键数: {len(foreign_keys)}")
        print(f"  索引数: {len(indexes)}")
    
    # 保存表结构信息到JSON文件
    with open('table_schemas.json', 'w') as f:
        json.dump(schema_info, f, indent=2)
    print(f"\n表结构信息已保存到 table_schemas.json")
    
    # 生成Alembic创建表的代码
    print("\n生成Alembic创建表代码:")
    
    # 示例代码片段
    for table_name in sorted(table_names):
        if table_name == 'alembic_version':  # 跳过alembic版本表
            continue
            
        print(f"""
    # {table_name}表
    if '{table_name}' not in tables:
        op.create_table(
            '{table_name}',
            # 在这里添加列定义
            # ...
        )
        # 在这里添加索引创建
        # ...
    """)
    
    print("\n请手动完成列定义和索引创建部分")

if __name__ == "__main__":
    main() 