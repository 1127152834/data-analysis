#!/bin/bash

# 创建临时目录
mkdir -p /tmp/fix-nextjs

# 将修改后的本地文件推送到服务器
echo "将所有页面文件修改为异步函数..."

# 查找并修改所有页面文件
find ./frontend/app/src/app -name "*page.tsx" -type f -exec grep -l "export default function.*params" {} \; | while read file; do
  echo "处理文件: $file"
  # 备份原始文件
  cp "$file" "${file}.bak"
  # 修改为异步函数
  sed -i 's/export default function \([a-zA-Z0-9_]*\)(/export default async function \1(/g' "$file"
  echo "已更新: $file"
done

echo "所有文件处理完成!"
echo "请使用以下命令重新构建docker容器:"
echo "docker-compose -f docker-compose.dev.yml build frontend --no-cache"
echo "docker-compose -f docker-compose.dev.yml up -d" 