#!/bin/bash

echo "开始修复Next.js页面组件..."

# 查找所有页面文件
PAGES=$(find ./frontend/app/src/app -name "*page.tsx" -type f)

for file in $PAGES; do
  echo "检查文件: $file"
  
  # 检查文件是否包含'use client'指令
  if grep -q "'use client'" "$file"; then
    echo "这是客户端组件，保持同步函数: $file"
    # 确保客户端组件使用同步函数
    if grep -q "export default async function" "$file"; then
      echo "  修复客户端组件中的异步函数..."
      sed -i 's/export default async function \([a-zA-Z0-9_]*\)(/export default function \1(/g' "$file"
      echo "  已更新为同步函数: $file"
    fi
  else
    echo "这是服务器组件，使用异步函数: $file"
    # 确保服务器组件使用异步函数
    if grep -q "export default function.*params" "$file" && ! grep -q "export default async function" "$file"; then
      echo "  修复服务器组件中的同步函数..."
      sed -i 's/export default function \([a-zA-Z0-9_]*\)(/export default async function \1(/g' "$file"
      echo "  已更新为异步函数: $file"
    fi
  fi
done

echo "所有页面组件已处理完毕!"
echo ""
echo "请使用以下命令重新构建docker容器:"
echo "docker-compose -f docker-compose.dev.yml build frontend --no-cache"
echo "docker-compose -f docker-compose.dev.yml up -d" 