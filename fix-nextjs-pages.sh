#!/bin/bash

# 检查操作系统类型
if [[ "$OSTYPE" == "darwin"* ]]; then
  # MacOS
  echo "Running on MacOS"
  # 查找所有包含params参数的页面组件
  FILES=$(find frontend/app/src/app -name "*page.tsx" -type f -exec grep -l "export default function.*params" {} \;)

  # 对每个文件进行修改
  for file in $FILES; do
    echo "Processing $file"
    # 使用MacOS兼容的sed命令
    sed -i '' 's/export default function \([a-zA-Z0-9_]*\)(/export default async function \1(/g' "$file"
    echo "Updated $file"
  done
else
  # Linux
  echo "Running on Linux"
  # 查找所有包含params参数的页面组件
  FILES=$(find frontend/app/src/app -name "*page.tsx" -type f -exec grep -l "export default function.*params" {} \;)

  # 对每个文件进行修改
  for file in $FILES; do
    echo "Processing $file"
    # 将非异步函数转换为异步函数
    sed -i 's/export default function \([a-zA-Z0-9_]*\)(/export default async function \1(/g' "$file"
    echo "Updated $file"
  done
fi

echo "All files have been processed." 