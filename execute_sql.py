#!/usr/bin/env python3
"""
执行SQL文件的Python脚本
可以读取并执行当前目录下的test.sql文件，或者通过命令行参数指定其他SQL文件
"""

import os
import sys
import argparse
import pymysql
from pymysql.cursors import DictCursor
import time

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='执行SQL文件')
    parser.add_argument('--file', '-f', type=str, default='test.sql', 
                        help='要执行的SQL文件 (默认: test.sql)')
    parser.add_argument('--host', '-H', type=str, default='127.0.0.1',
                        help='TiDB主机地址 (默认: 127.0.0.1)')
    parser.add_argument('--port', '-p', type=int, default=4000,
                        help='TiDB端口 (默认: 4000)')
    parser.add_argument('--user', '-u', type=str, default='root',
                        help='TiDB用户名 (默认: root)')
    parser.add_argument('--password', '-P', type=str, default='',
                        help='TiDB密码 (默认: 空)')
    parser.add_argument('--database', '-d', type=str, default='test',
                        help='TiDB数据库名 (默认: test)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='显示详细执行信息')
    return parser.parse_args()

def read_sql_file(file_path):
    """读取SQL文件内容"""
    if not os.path.exists(file_path):
        print(f"错误：文件 '{file_path}' 不存在")
        sys.exit(1)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"读取文件时出错：{e}")
        sys.exit(1)

def split_sql_statements(sql_content):
    """
    将SQL文件内容分割成单独的SQL语句
    处理基本的SQL语句分隔，包括语句结束的分号和多行SQL
    """
    statements = []
    current_statement = []
    multiline_comment = False
    single_line_comment = False
    
    for line in sql_content.splitlines():
        line = line.strip()
        
        # 跳过空行
        if not line:
            continue
        
        # 处理多行注释
        if '/*' in line and '*/' not in line:
            multiline_comment = True
            continue
        
        if '*/' in line and multiline_comment:
            multiline_comment = False
            continue
        
        if multiline_comment:
            continue
        
        # 处理单行注释
        if line.startswith('--') or line.startswith('#'):
            continue
        
        # 去除行尾注释
        comment_pos = line.find('--')
        if comment_pos >= 0:
            line = line[:comment_pos].strip()
        
        comment_pos = line.find('#')
        if comment_pos >= 0:
            line = line[:comment_pos].strip()
        
        if not line:
            continue
        
        # 添加到当前语句
        current_statement.append(line)
        
        # 检查语句是否结束
        if line.endswith(';'):
            statements.append(' '.join(current_statement))
            current_statement = []
    
    # 处理最后一条没有分号的语句
    if current_statement:
        statements.append(' '.join(current_statement))
    
    return statements

def execute_sql(args):
    """连接TiDB并执行SQL语句"""
    # 连接配置
    db_config = {
        'host': args.host,
        'port': args.port,
        'user': args.user,
        'password': args.password,
        'database': args.database,
        'charset': 'utf8mb4',
        'cursorclass': DictCursor
    }
    
    # 读取SQL文件
    sql_content = read_sql_file(args.file)
    sql_statements = split_sql_statements(sql_content)
    
    if args.verbose:
        print(f"共解析出 {len(sql_statements)} 条SQL语句")
    
    try:
        # 连接数据库
        print(f"正在连接数据库 {args.host}:{args.port}...")
        connection = pymysql.connect(**db_config)
        print("连接成功！")
        
        with connection:
            # 创建游标
            with connection.cursor() as cursor:
                for i, statement in enumerate(sql_statements):
                    if not statement.strip():
                        continue
                    
                    try:
                        if args.verbose:
                            print(f"\n执行语句 {i+1}/{len(sql_statements)}:")
                            print(f"{statement}")
                        
                        start_time = time.time()
                        affected_rows = cursor.execute(statement)
                        end_time = time.time()
                        
                        if statement.strip().lower().startswith('select'):
                            result = cursor.fetchall()
                            if args.verbose:
                                print(f"查询结果 ({len(result)} 行):")
                                if result and len(result) <= 10:
                                    for row in result:
                                        print(row)
                                elif result:
                                    print(f"(显示前5行，共 {len(result)} 行)")
                                    for row in result[:5]:
                                        print(row)
                        else:
                            print(f"语句 {i+1}: 成功执行，影响 {affected_rows} 行，用时 {end_time - start_time:.4f} 秒")
                    
                    except Exception as e:
                        print(f"语句 {i+1} 执行失败: {e}")
                        if args.verbose:
                            print(f"失败的SQL: {statement}")
                        
                        # 询问是否继续
                        choice = input("\n是否继续执行后续语句? (y/n): ").lower()
                        if choice != 'y':
                            print("执行终止")
                            return
            
            # 提交事务
            connection.commit()
            print("\n所有SQL语句执行完成！")
    
    except Exception as e:
        print(f"数据库连接或执行错误: {e}")
        sys.exit(1)

def main():
    """主函数"""
    args = parse_args()
    execute_sql(args)

if __name__ == "__main__":
    main() 