# AutoFlow (tidb-ai) 项目汉化指南

本文档提供了AutoFlow项目的全面汉化方案，包括前端界面、后端提示、代码注释和文档的汉化流程与最佳实践。

## 一、汉化范围与规划

### 1.1 汉化范围

AutoFlow项目的汉化范围主要包括以下几个方面：

1. **前端用户界面**
   - 导航菜单
   - 按钮文本
   - 表单标签
   - 提示信息
   - 错误信息
   - 页面标题和描述

2. **后端返回消息**
   - API响应消息
   - 错误提示
   - 日志信息

3. **代码注释**
   - 函数和类的文档字符串
   - 关键代码段的解释性注释

4. **项目文档**
   - 用户指南
   - 开发文档
   - API文档
   - 部署文档

### 1.2 汉化原则

在进行汉化工作时，应遵循以下原则：

1. **保持专业性**：术语翻译准确，避免使用网络流行语
2. **保持一致性**：同一术语在整个项目中使用统一翻译
3. **符合中文表达习惯**：不生硬直译，注重自然流畅的中文表达
4. **保留必要的英文术语**：特定技术术语可保留英文，但需加中文解释
5. **注重语境**：根据上下文语境选择合适的翻译

### 1.3 汉化优先级

按照以下优先级进行汉化工作：

1. 用户直接可见的界面元素
2. 错误和提示信息
3. 用户文档
4. 开发文档和代码注释

## 二、前端界面汉化

### 2.1 国际化框架搭建

前端采用模块化的国际化方案：

1. 创建语言文件目录结构：

```
frontend/app/src/lib/
└── i18n/
    ├── index.ts        # 国际化入口
    ├── zh-CN.ts        # 中文翻译
    └── en.ts           # 英文翻译(原文)
```

2. 在 `zh-CN.ts` 中定义翻译内容：

```typescript
// src/lib/i18n/zh-CN.ts
export const translations = {
  common: {
    search: "搜索",
    cancel: "取消",
    confirm: "确认",
    delete: "删除",
    edit: "编辑",
    save: "保存",
    create: "创建",
    close: "关闭",
    loading: "加载中...",
    noData: "暂无数据",
    more: "更多",
    back: "返回",
  },
  nav: {
    home: "首页",
    chat: "聊天",
    knowledgeBase: "知识库",
    settings: "设置",
    admin: "管理",
    documents: "文档",
    profile: "个人资料",
    logout: "退出登录",
  },
  auth: {
    login: "登录",
    register: "注册",
    forgotPassword: "忘记密码",
    email: "邮箱",
    password: "密码",
    username: "用户名",
    loginSuccess: "登录成功",
    loginFailed: "登录失败",
  },
  chat: {
    newChat: "新建对话",
    sendMessage: "发送消息",
    inputPlaceholder: "输入您的问题...",
    thinking: "思考中...",
    regenerate: "重新生成",
    copy: "复制",
    feedback: "反馈",
    chatHistory: "对话历史",
    deleteChat: "删除对话",
    sources: "参考资料",
  },
  knowledgeBase: {
    title: "知识库",
    create: "创建知识库",
    edit: "编辑知识库",
    delete: "删除知识库",
    upload: "上传文档",
    name: "名称",
    description: "描述",
    documents: "文档数量",
    lastUpdated: "最后更新时间",
    uploadDocument: "上传文档",
    processing: "处理中",
    processed: "已处理",
    failed: "处理失败",
  },
  admin: {
    dashboard: "仪表盘",
    users: "用户管理",
    llms: "LLM模型",
    embeddingModels: "嵌入模型",
    rerankerModels: "重排模型",
    siteSettings: "站点设置",
    apiKeys: "API密钥",
    logs: "系统日志",
    stats: "使用统计",
  },
  models: {
    provider: "提供商",
    name: "模型名称",
    apiKey: "API密钥",
    endpoint: "API端点",
    defaultModel: "默认模型",
    temperature: "温度",
    maxTokens: "最大Token数",
    testModel: "测试模型",
  },
  errors: {
    generic: "发生错误，请稍后重试",
    notFound: "未找到请求的资源",
    unauthorized: "未授权的访问",
    invalidInput: "输入无效",
    serverError: "服务器错误",
    networkError: "网络错误，请检查您的连接",
  },
  // 其他翻译...
};
```

3. 创建翻译钩子函数：

```typescript
// src/lib/i18n/index.ts
import { translations as zhCN } from './zh-CN';

export type TranslationKey = string;

export function useTranslation() {
  // 可扩展为支持语言切换
  const translations = zhCN;
  
  const t = (key: TranslationKey): string => {
    const keys = key.split('.');
    let result: any = translations;
    
    for (const k of keys) {
      if (result[k] === undefined) {
        console.warn(`Translation key not found: ${key}`);
        return key; // 如果找不到翻译，返回key作为后备
      }
      result = result[k];
    }
    
    return result;
  };
  
  return { t };
}
```

4. 在组件中使用翻译：

```tsx
import { useTranslation } from '@/lib/i18n';

export function Header() {
  const { t } = useTranslation();
  
  return (
    <header>
      <nav>
        <ul>
          <li><a href="/">{t('nav.home')}</a></li>
          <li><a href="/chat">{t('nav.chat')}</a></li>
          <li><a href="/knowledge-base">{t('nav.knowledgeBase')}</a></li>
        </ul>
      </nav>
    </header>
  );
}
```

### 2.2 汉化静态文本

1. 替换硬编码的英文文本：

```tsx
// 原代码
<button>Search</button>

// 汉化后
<button>{t('common.search')}</button>
```

2. 汉化表单标签和占位符：

```tsx
// 原代码
<label>Email</label>
<input placeholder="Enter your email" />

// 汉化后
<label>{t('auth.email')}</label>
<input placeholder={t('auth.emailPlaceholder')} />
```

3. 汉化提示和错误消息：

```tsx
// 原代码
toast.success("Operation completed successfully");

// 汉化后
toast.success(t('messages.operationSuccess'));
```

### 2.3 汉化动态内容

对于从后端API返回的动态内容，需要修改后端代码以返回中文内容。同时，前端也需要相应调整：

```tsx
// 假设API返回的错误信息是英文
try {
  // API调用
} catch (error) {
  // 原代码
  setError(error.message);
  
  // 汉化后 - 基于错误码映射中文信息
  setError(mapErrorToChineseMessage(error.code));
}

// 错误码到中文消息的映射
function mapErrorToChineseMessage(errorCode: string): string {
  const errorMap: Record<string, string> = {
    'ERR_INVALID_INPUT': t('errors.invalidInput'),
    'ERR_NOT_FOUND': t('errors.notFound'),
    // 其他错误码...
  };
  
  return errorMap[errorCode] || t('errors.generic');
}
```

## 三、后端汉化

### 3.1 异常消息汉化

修改 `app/exceptions.py` 文件中的异常消息：

```python
# 原代码
class ResourceNotFoundException(Exception):
    def __init__(self, resource_type="Resource", resource_id=None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message)

# 汉化后
class ResourceNotFoundException(Exception):
    def __init__(self, resource_type="资源", resource_id=None):
        message = f"未找到{resource_type}"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message)
```

### 3.2 API响应汉化

修改API响应中的消息文本：

```python
# 原代码
@router.post("/items")
async def create_item(item: Item):
    # ...
    return {"message": "Item created successfully", "item": item}

# 汉化后
@router.post("/items")
async def create_item(item: Item):
    # ...
    return {"message": "项目创建成功", "item": item}
```

### 3.3 日志消息汉化

修改日志消息为中文：

```python
# 原代码
logger.info(f"Processing document {document_id}")
logger.error(f"Failed to process document {document_id}: {error}")

# 汉化后
logger.info(f"正在处理文档 {document_id}")
logger.error(f"处理文档 {document_id} 失败: {error}")
```

### 3.4 LLM提示模板汉化

修改LLM提示模板为中文：

```python
# 原代码
system_prompt = """
You are a helpful assistant. Answer the user question based on the following context.
Context: {context}

If you don't know the answer, say you don't know. Don't make up information.
"""

# 汉化后
system_prompt = """
你是一个有帮助的助手。请根据以下上下文回答用户的问题。
上下文: {context}

如果你不知道答案，请直说你不知道。不要编造信息。
"""
```

## 四、代码注释汉化

### 4.1 Python代码注释汉化

汉化Python文件中的文档字符串和注释：

```python
# 原代码
def process_document(document_id: str) -> Dict[str, Any]:
    """
    Process a document and extract its content.
    
    Args:
        document_id: The ID of the document to process
        
    Returns:
        A dictionary containing the processed content
    """
    # Get document from database
    document = get_document(document_id)
    
    # Process document
    content = extract_content(document)
    
    return {"id": document_id, "content": content}

# 汉化后
def process_document(document_id: str) -> Dict[str, Any]:
    """
    处理文档并提取其内容。
    
    参数:
        document_id: 要处理的文档ID
        
    返回:
        包含处理后内容的字典
    """
    # 从数据库获取文档
    document = get_document(document_id)
    
    # 处理文档
    content = extract_content(document)
    
    return {"id": document_id, "content": content}
```

### 4.2 TypeScript/JavaScript代码注释汉化

汉化TypeScript文件中的JSDoc注释：

```typescript
// 原代码
/**
 * Fetch data from the API and handle errors
 * @param endpoint - The API endpoint to fetch data from
 * @param options - Request options
 * @returns The fetched data
 * @throws Error if the fetch operation fails
 */
async function fetchData(endpoint: string, options?: RequestOptions): Promise<any> {
  try {
    const response = await fetch(endpoint, options);
    // Check if response is ok
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    // Log and rethrow error
    console.error('Fetch error:', error);
    throw error;
  }
}

// 汉化后
/**
 * 从API获取数据并处理错误
 * @param endpoint - 要获取数据的API端点
 * @param options - 请求选项
 * @returns 获取到的数据
 * @throws 如果获取操作失败则抛出错误
 */
async function fetchData(endpoint: string, options?: RequestOptions): Promise<any> {
  try {
    const response = await fetch(endpoint, options);
    // 检查响应是否正常
    if (!response.ok) {
      throw new Error(`API错误: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    // 记录并重新抛出错误
    console.error('获取数据错误:', error);
    throw error;
  }
}
```

## 五、文档汉化

### 5.1 用户指南汉化

将 `docs/src/content` 下的文档内容进行翻译：

1. 创建中文文档目录：

```
docs/src/content/zh/
```

2. 将现有的英文Markdown文档翻译并放置在中文目录下：

原文档：
```markdown
# Quick Start

This guide will help you get started with AutoFlow quickly.

## Prerequisites

Before you begin, make sure you have:
- Deployed the AutoFlow system
- Created an admin account
- Configured TiDB database connection
```

汉化后：
```markdown
# 快速入门

本指南将帮助您快速开始使用AutoFlow。

## 前提条件

在开始之前，请确保您已经：
- 部署了AutoFlow系统
- 创建了管理员账户
- 配置了TiDB数据库连接
```

### 5.2 API文档汉化

汉化FastAPI生成的API文档：

```python
# 原代码
@router.get("/items/{item_id}", response_model=Item)
async def read_item(
    item_id: UUID,
    current_user: User = Depends(current_active_user),
) -> Item:
    """
    Get a specific item by ID.
    
    - **item_id**: The ID of the item to retrieve
    """
    # ...

# 汉化后
@router.get("/items/{item_id}", response_model=Item)
async def read_item(
    item_id: UUID,
    current_user: User = Depends(current_active_user),
) -> Item:
    """
    通过ID获取特定项目。
    
    - **item_id**: 要检索的项目ID
    """
    # ...
```

### 5.3 部署文档汉化

将部署指南文档翻译为中文，包括部署步骤、配置说明和故障排除指南。

## 六、汉化工具与自动化

### 6.1 文本提取工具

创建脚本自动提取需要翻译的文本：

```python
# scripts/extract_texts.py
import os
import re
import json
from pathlib import Path

def extract_texts_from_tsx(file_path):
    """从TSX文件中提取硬编码的英文文本"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取各种模式的文本
    patterns = [
        r'<[^>]*>([A-Za-z\s]+)<\/[^>]*>',  # HTML标签中的文本
        r'placeholder="([^"]*)"',           # 占位符文本
        r'title="([^"]*)"',                 # 标题属性
        r'toast\.(success|error|info)\("([^"]*)"\)',  # Toast消息
    ]
    
    texts = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            if isinstance(matches[0], tuple):
                # 如果匹配结果是元组（如toast消息），取第二个元素
                texts.extend([m[1] for m in matches])
            else:
                texts.extend(matches)
    
    return texts

def extract_texts_from_py(file_path):
    """从Python文件中提取硬编码的英文文本"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 提取各种模式的文本
    patterns = [
        r'["\']([\w\s]+)["\']',             # 引号中的文本
        r'message="([^"]*)"',               # 消息参数
        r'logger\.(info|error|warning)\(f?"([^"]*)"', # 日志消息
    ]
    
    texts = []
    for pattern in patterns:
        matches = re.findall(pattern, content)
        if matches:
            if isinstance(matches[0], tuple):
                texts.extend([m[1] for m in matches])
            else:
                texts.extend(matches)
    
    return texts

def main():
    # 设置要扫描的目录
    frontend_dir = Path('../frontend')
    backend_dir = Path('../backend')
    
    # 结果字典
    results = {
        'frontend': {},
        'backend': {}
    }
    
    # 扫描前端文件
    for ext in ['.tsx', '.ts', '.jsx', '.js']:
        for file in frontend_dir.rglob(f'*{ext}'):
            if 'node_modules' not in str(file):
                texts = extract_texts_from_tsx(file)
                if texts:
                    results['frontend'][str(file.relative_to(frontend_dir))] = texts
    
    # 扫描后端文件
    for ext in ['.py']:
        for file in backend_dir.rglob(f'*{ext}'):
            texts = extract_texts_from_py(file)
            if texts:
                results['backend'][str(file.relative_to(backend_dir))] = texts
    
    # 保存结果到JSON文件
    with open('texts_to_translate.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"提取完成。要翻译的文本已保存到 texts_to_translate.json")

if __name__ == "__main__":
    main()
```

### 6.2 自动替换工具

创建脚本自动替换已翻译的文本：

```python
# scripts/apply_translations.py
import os
import re
import json
from pathlib import Path

def apply_translations_to_file(file_path, translations, is_tsx=True):
    """将翻译应用到文件中"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 为每个原文创建替换函数
    for original, translated in translations.items():
        if not original or not translated:
            continue
        
        if is_tsx:
            # 对于TSX/JS文件，将文本替换为t()调用
            pattern = f'([>"])({re.escape(original)})([<"])'
            replacement = f'\\1{{{t("{translated}")}}\\3'
            content = re.sub(pattern, replacement, content)
            
            # 替换其他模式
            patterns = [
                (f'placeholder="{re.escape(original)}"', f'placeholder={{{t("{translated}")}}}'),
                (f'title="{re.escape(original)}"', f'title={{{t("{translated}")}}}'),
                (f'toast\\.(success|error|info)\\("{re.escape(original)}"\\)', f'toast.\\1({t("{translated}")})'),
            ]
            
            for p, r in patterns:
                content = re.sub(p, r, content)
        else:
            # 对于Python文件，直接替换文本
            content = content.replace(f'"{original}"', f'"{translated}"')
            content = content.replace(f"'{original}'", f"'{translated}'")
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

def main():
    # 加载翻译
    with open('translations.json', 'r', encoding='utf-8') as f:
        translations = json.load(f)
    
    # 设置要处理的目录
    frontend_dir = Path('../frontend')
    backend_dir = Path('../backend')
    
    # 处理前端文件
    for file_path, file_translations in translations['frontend'].items():
        full_path = frontend_dir / file_path
        if full_path.exists():
            apply_translations_to_file(full_path, file_translations, is_tsx=True)
            print(f"已应用翻译到: {file_path}")
    
    # 处理后端文件
    for file_path, file_translations in translations['backend'].items():
        full_path = backend_dir / file_path
        if full_path.exists():
            apply_translations_to_file(full_path, file_translations, is_tsx=False)
            print(f"已应用翻译到: {file_path}")
    
    print("翻译应用完成。")

if __name__ == "__main__":
    main()
```

## 七、汉化验证与测试

### 7.1 汉化验证清单

- [ ] 所有页面标题、按钮和标签已汉化
- [ ] 所有表单占位符和提示已汉化
- [ ] 所有错误和成功消息已汉化
- [ ] 下拉菜单和选项已汉化
- [ ] 模态框和对话框内容已汉化
- [ ] 邮件模板已汉化
- [ ] 导航和面包屑已汉化
- [ ] 日期和时间格式符合中文习惯
- [ ] 管理后台页面已汉化

### 7.2 界面测试

1. 对每个页面进行截图，与汉化前对比
2. 验证长文本显示是否正常，避免布局错乱
3. 检查特殊字符是否正确显示
4. 测试不同浏览器和设备上的显示效果

### 7.3 功能测试

1. 测试所有表单的提交和验证
2. 检查错误处理和提示信息
3. 验证搜索和筛选功能的中文支持
4. 测试知识库中文文档的导入和处理

## 八、常见汉化问题与解决方案

### 8.1 文本长度问题

**问题**: 汉化后的文本长度可能与原文不同，导致界面布局错乱

**解决方案**:
1. 使用更简洁的中文表达
2. 确保UI组件使用弹性布局
3. 为长文本添加溢出处理样式
4. 必要时调整组件大小

```css
/* 文本溢出处理样式 */
.text-ellipsis {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

### 8.2 字符编码问题

**问题**: 某些环境下中文显示为乱码

**解决方案**:
1. 确保所有文件使用UTF-8编码
2. 检查数据库字符集设置
3. 添加正确的Content-Type头
4. 在HTML文件中添加正确的meta标签

```html
<meta charset="UTF-8">
```

### 8.3 日期和时间格式

**问题**: 日期和时间格式与中文习惯不符

**解决方案**:
创建符合中文习惯的日期格式化函数：

```typescript
// 中文日期格式化函数
function formatDateCN(date: Date): string {
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}

// 中文时间格式化函数
function formatTimeCN(date: Date): string {
  return `${date.getHours()}时${date.getMinutes()}分${date.getSeconds()}秒`;
}

// 中文日期时间格式化函数
function formatDateTimeCN(date: Date): string {
  return `${formatDateCN(date)} ${formatTimeCN(date)}`;
}
```

### 8.4 RTL支持问题

**问题**: 汉化后页面可能有RTL(从右到左)支持问题

**解决方案**:
1. 确保在HTML中设置正确的语言属性
2. 检查CSS中的方向相关属性
3. 避免使用依赖方向的绝对定位

```html
<html lang="zh-CN" dir="ltr">
```

## 九、维护与更新

### 9.1 翻译词汇表

创建并维护一个标准化的翻译词汇表，确保术语翻译的一致性：

| 英文术语 | 中文翻译 | 说明 |
|---------|---------|------|
| Knowledge Base | 知识库 | 存储文档和信息的仓库 |
| Embedding Model | 嵌入模型 | 将文本转换为向量的模型 |
| Reranker Model | 重排模型 | 优化搜索结果排序的模型 |
| Chat Engine | 聊天引擎 | 处理对话交互的引擎 |
| Document Chunking | 文档分块 | 将长文档分割成小块的处理 |
| Vector Storage | 向量存储 | 存储和检索向量的数据库 |
| RAG | 检索增强生成 | Retrieval-Augmented Generation的缩写 |
| GraphRAG | 图检索增强生成 | 基于知识图谱的检索增强生成 |

### 9.2 持续更新机制

建立持续更新汉化内容的机制：

1. 新功能开发同步进行汉化
2. 定期检查和更新翻译
3. 收集用户反馈，优化翻译质量
4. 建立翻译审核流程

### 9.3 翻译贡献指南

为社区贡献者提供翻译指南：

1. 明确翻译流程和工具
2. 提供翻译标准和规范
3. 说明提交翻译的方式
4. 建立翻译审核和合并机制

## 十、附录：术语表

| 英文 | 中文 | 说明 |
|-----|-----|-----|
| admin | 管理员 | 系统管理员用户 |
| API key | API密钥 | 访问API的认证密钥 |
| authentication | 认证 | 验证用户身份的过程 |
| authorization | 授权 | 确定用户权限的过程 |
| chunk | 块/分块 | 文档的分割单位 |
| context | 上下文 | LLM生成回答时参考的相关信息 |
| dashboard | 仪表盘 | 管理界面的主页 |
| embedding | 嵌入/向量化 | 将文本转换为向量的过程 |
| feedback | 反馈 | 用户对系统回答的评价 |
| knowledge base | 知识库 | 存储知识的仓库 |
| prompt | 提示词 | 给LLM的指令和上下文 |
| query | 查询 | 用户的问题或搜索词 |
| retrieval | 检索 | 从知识库获取相关信息的过程 |
| source | 来源 | 信息的出处 |
| vector | 向量 | 文本的数值表示形式 |
</rewritten_file> 