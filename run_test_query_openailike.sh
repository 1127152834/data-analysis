#!/bin/bash

# 转到项目根目录
cd "$(dirname "$0")"

# 运行测试脚本
echo "开始运行SQL查询工具测试 (OpenAILike版)..."
python scripts/test_sql_query_tool_litellm.py
