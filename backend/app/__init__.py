import os
import sys

# 添加当前路径到模块搜索路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入TiFlash补丁，确保在其他模块导入前修复
try:
    import tiflash_patch
except ImportError:
    print("警告: 未能导入TiFlash补丁模块，向量索引功能可能受到影响")

# 设置环境变量，启用LiteLLM本地模型成本映射功能
# 这允许系统跟踪本地部署的大型语言模型的使用成本
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
