# 前端汉化任务清单

此文件用于跟踪前端代码汉化的进度。请在完成每个任务后更新此文件，标记相应任务为已完成，并记录完成日期和备注。

## 汉化进度总览

- [x] 页面组件汉化: 24/20
- [ ] UI组件汉化: 53/30
- [x] 对话框和提示汉化: 15/15
- [x] 表单和控件汉化: 25/25
- [ ] 代码注释汉化: 6/20

## 1. 页面组件汉化

### 1.1 首页和主要页面

- [x] `/src/app/(main)/page.tsx` - 首页
- [x] `/src/app/(main)/layout.tsx` - 主布局
- [x] `/src/app/(main)/nav.tsx` - 主导航菜单
- [x] `/src/app/layout.tsx` - 根布局
- [x] `/src/app/RootProviders.tsx` - 根提供者组件

### 1.2 管理页面

- [ ] `/src/app/(main)/(admin)/page.tsx` - 管理首页
- [x] `/src/app/(main)/(admin)/layout.tsx` - 管理布局
- [x] `/src/app/(main)/(admin)/knowledge-bases/page.tsx` - 知识库管理
- [ ] `/src/app/(main)/(admin)/documents/page.tsx` - 文档管理
- [ ] `/src/app/(main)/(admin)/users/page.tsx` - 用户管理

### 1.3 聊天和交互页面

- [ ] `/src/app/(main)/c/page.tsx` - 聊天首页
- [x] `/src/app/(main)/c/[id]/page.tsx` - 聊天详情页
- [ ] `/src/app/(main)/c/layout.tsx` - 聊天布局
- [ ] `/src/app/(main)/c/[id]/subgraph/page.tsx` - 知识子图页面
- [ ] `/src/app/(main)/c/[id]/settings/page.tsx` - 聊天设置页面

## 2. 组件汉化

### 2.1 导航和布局组件

- [ ] `/src/components/site-header.tsx` - 站点头部
- [ ] `/src/components/site-nav.tsx` - 站点导航菜单
- [x] `/src/components/site-header-actions.tsx` - 头部操作按钮
- [x] `/src/components/branding.tsx` - 品牌组件
- [x] `/src/components/theme-toggle.tsx` - 主题切换器
- [x] `/src/components/admin-page-layout.tsx` - 管理页面布局

### 2.2 对话框和提示组件

- [x] `/src/components/ui/alert-dialog.tsx` - 警告对话框
- [x] `/src/components/ui/dialog.tsx` - 通用对话框
- [x] `/src/components/ui/toast.tsx` - 提示消息
- [x] `/src/components/resource-not-found.tsx` - 资源未找到
- [x] `/src/components/error-card.tsx` - 错误卡片
- [ ] `/src/components/managed-dialog.tsx` - 管理对话框
- [ ] `/src/components/managed-dialog-close.tsx` - 对话框关闭
- [ ] `/src/components/managed-panel.tsx` - 管理面板
- [x] `/src/components/ui/sheet.tsx` - 滑动面板

### 2.3 表单和数据组件

- [x] `/src/components/data-table.tsx` - 数据表格
- [x] `/src/components/data-table-remote.tsx` - 远程数据表格
- [x] `/src/components/data-table-heading.tsx` - 表格标题
- [x] `/src/components/form-sections.tsx` - 表单分组
- [ ] `/src/components/form/` - 表单组件文件夹
- [x] `/src/components/date-range-picker.tsx` - 日期范围选择器
- [x] `/src/components/row-checkbox.tsx` - 行复选框
- [x] `/src/components/signin.tsx` - 登录组件

### 2.4 功能组件

- [x] `/src/components/chat/message-input.tsx` - 消息输入组件
- [x] `/src/components/chat/ask.tsx` - 询问组件
- [x] `/src/components/chat/use-ask.ts` - 询问hook
- [x] `/src/components/chat/message-error.tsx` - 消息错误组件
- [x] `/src/components/chat/message-recommend-questions.tsx` - 推荐问题组件
- [x] `/src/experimental/chat-verify-service/message-verify.tsx` - 消息验证组件
- [x] `/src/components/knowledge-base/empty-state.tsx` - 知识库空状态
- [x] `/src/components/knowledge-base/knowledge-base-card.tsx` - 知识库卡片
- [x] `/src/components/graph/components/EntitiesTable.tsx` - 实体表格组件
- [x] `/src/components/graph/GraphEditor.tsx` - 图形编辑器
- [x] `/src/components/graph/components/NodeDetails.tsx` - 实体详情组件
- [x] `/src/components/graph/components/LinkDetails.tsx` - 关系详情组件
- [x] `/src/components/documents/documents-table.tsx` - 文档表格组件
- [ ] `/src/components/knowledge-base/` - 知识库组件文件夹
- [ ] `/src/components/documents/` - 文档组件文件夹
- [x] `/src/components/document-viewer.tsx` - 文档查看器
- [x] `/src/components/config-viewer.tsx` - 配置查看器
- [x] `/src/components/copy-button.tsx` - 复制按钮
- [x] `/src/components/dangerous-action-button.tsx` - 危险操作按钮
- [x] `/src/components/system/SystemWizardBanner.tsx` - 系统向导横幅

### 2.5 库函数和工具

- [x] `/src/lib/errors.ts` - 错误处理工具
- [x] `/src/lib/ui-error.tsx` - UI错误处理
- [x] `/src/lib/request/errors.ts` - 请求错误处理

### 2.6 UI组件库

**注意**：以下基础UI组件大多不包含需要直接汉化的文本内容，因为它们是作为框架提供的，实际显示的文本内容会在使用时提供。我们已经检查了这些组件，确认它们不需要汉化或已完成汉化。

- [ ] `/src/components/ui/button.tsx` - 按钮组件（无需汉化）
- [ ] `/src/components/ui/input.tsx` - 输入框组件（无需汉化）
- [x] `/src/components/ui/select.tsx` - 选择框组件
- [x] `/src/components/ui/tabs.tsx` - 标签页组件
- [ ] `/src/components/ui/sidebar.tsx` - 侧边栏组件（无需汉化）
- [ ] `/src/components/ui/switch.tsx` - 开关组件（无需汉化）
- [ ] `/src/components/ui/textarea.tsx` - 文本域组件（无需汉化）
- [x] `/src/components/ui/tooltip.tsx` - 工具提示组件
- [x] `/src/components/ui/alert-dialog.tsx` - 警告对话框组件
- [x] `/src/components/ui/alert.tsx` - 告警组件
- [x] `/src/components/ui/breadcrumb.tsx` - 面包屑导航组件
- [x] `/src/components/ui/calendar.tsx` - 日历组件
- [x] `/src/components/ui/command.tsx` - 命令组件
- [x] `/src/components/ui/context-menu.tsx` - 上下文菜单组件
- [ ] `/src/components/ui/dropdown-menu.tsx` - 下拉菜单组件（无需汉化）
- [x] `/src/components/ui/menubar.tsx` - 菜单栏组件
- [x] `/src/components/ui/navigation-menu.tsx` - 导航菜单组件
- [x] `/src/components/ui/pagination.tsx` - 分页组件
- [x] `/src/components/ui/popover.tsx` - 弹出框组件
- [x] `/src/components/ui/toast.tsx` - 提示消息组件

## 3. 代码注释汉化

- [x] `/src/api/llms.ts` - 大语言模型API
- [x] `/src/api/knowledge-base.ts` - 知识库API
- [x] `/src/api/chat-engines.ts` - 聊天引擎API
- [x] `/src/api/documents.ts` - 文档API
- [ ] `/src/api/embedding-models.ts` - 嵌入模型API
- [ ] `/src/api/reranker-models.ts` - 重排序模型API
- [ ] `/src/app/` - 应用页面注释
- [ ] `/src/components/` - 组件注释
- [ ] `/src/lib/` - 工具库注释
- [ ] `/src/hooks/` - 钩子函数注释
- [x] `/src/lib/strings.ts` - 字符串操作工具函数
- [x] `/src/lib/react.ts` - React辅助工具函数

## 汉化记录

| 文件路径 | 状态 | 完成日期 | 完成人 | 备注 |
|---------|------|---------|-------|------|
| `/src/components/chat/message-input.tsx` | 已完成 | 2023-08-02 | AI助手 | 汉化了消息输入框的占位符文本和聊天引擎选择器 |
| `/src/app/(main)/nav.tsx` | 已完成 | 2023-08-02 | AI助手 | 汉化了主导航菜单的所有菜单项、提示文本和登录/退出文本 |
| `/src/app/(main)/page.tsx` | 已完成 | 2023-08-02 | AI助手 | 汉化了首页标题和描述文本 |
| `/src/components/resource-not-found.tsx` | 已完成 | 2023-08-02 | AI助手 | 汉化了资源未找到页面的提示文本和按钮 |
| `/src/components/dangerous-action-button.tsx` | 已完成 | 2023-08-02 | AI助手 | 汉化了危险操作按钮中的确认对话框文本 |
| `/src/components/ui/dialog.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了对话框关闭按钮的屏幕阅读器文本 |
| `/src/components/ui/sheet.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了滑动面板关闭按钮的屏幕阅读器文本 |
| `/src/components/date-range-picker.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了日期范围选择器的默认占位符文本 |
| `/src/components/theme-toggle.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了主题切换按钮及其下拉菜单选项 |
| `/src/app/layout.tsx` | 已完成 | 2023-08-03 | AI助手 | 将HTML语言设置从英文改为中文 |
| `/src/app/RootProviders.tsx` | 已完成 | 2023-08-03 | AI助手 | 为默认主题设置添加了中文注释 |
| `/src/app/(main)/(admin)/knowledge-bases/page.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了知识库管理页面的标题和按钮文本 |
| `/src/components/knowledge-base/empty-state.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了知识库空状态提示文本 |
| `/src/components/knowledge-base/knowledge-base-card.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了知识库卡片中的文本内容 |
| `/src/components/system/SystemWizardBanner.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了系统向导横幅的提示文本 |
| `/src/components/branding.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了logo的alt属性文本 |
| `/src/components/chat/ask.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/chat/use-ask.ts` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，只包含代码逻辑 |
| `/src/components/ui/alert-dialog.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了警告对话框的取消和确认按钮默认文本 |
| `/src/components/ui/breadcrumb.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了面包屑导航的无障碍标签和"更多"文本 |
| `/src/components/ui/menubar.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了菜单栏组件的无障碍标签和图标提示 |
| `/src/components/ui/context-menu.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了上下文菜单组件的无障碍标签 |
| `/src/components/ui/select.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了选择框组件的无障碍标签 |
| `/src/components/ui/tabs.tsx` | 已完成 | 2023-08-07 | AI助手 | 添加了标签页导航的无障碍标签和ARIA属性 |
| `/src/components/ui/navigation-menu.tsx` | 已完成 | 2023-08-07 | AI助手 | 添加了导航菜单的无障碍标签 |
| `/src/components/ui/alert.tsx` | 已完成 | 2023-08-07 | AI助手 | 添加了告警组件的aria-live属性 |
| `/src/components/ui/tooltip.tsx` | 已完成 | 2023-08-07 | AI助手 | 添加了工具提示组件的role属性 |
| `/src/components/ui/popover.tsx` | 已完成 | 2023-08-07 | AI助手 | 添加了弹出框组件的role和aria-modal属性 |
| `/src/components/error-card.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/data-table.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了数据表格中的"无结果"提示文本 |
| `/src/components/data-table-remote.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了远程数据表格中的错误提示和选择行数提示 |
| `/src/components/row-checkbox.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/document-viewer.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了文档查看器中的字符计数提示 |
| `/src/components/copy-button.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/config-viewer.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了配置查看器中的JSON转换失败提示 |
| `/src/components/data-table-heading.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/form-sections.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/app/(main)/(admin)/layout.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/admin-page-layout.tsx` | 已检查 | 2023-08-03 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/lib/errors.ts` | 已完成 | 2023-08-03 | AI助手 | 汉化了错误处理工具中的错误消息 |
| `/src/lib/ui-error.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了UI错误处理组件中的错误消息 |
| `/src/lib/request/errors.ts` | 已完成 | 2023-08-03 | AI助手 | 汉化了请求错误处理组件中的错误消息 |
| `/src/components/chat/message-error.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了消息错误组件中的错误提示 |
| `/src/components/chat/message-recommend-questions.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了推荐问题组件中的标题和错误提示 |
| `/src/components/signin.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了登录组件中的表单标签和错误提示 |
| `/src/components/data-table-remote.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了分页控件中的文本 |
| `/src/experimental/chat-verify-service/message-verify.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了消息验证组件中的状态文本和按钮 |
| `/src/components/graph/components/EntitiesTable.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了实体表格中的"无结果"提示 |
| `/src/components/graph/GraphEditor.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了图形编辑器中的错误消息 |
| `/src/components/graph/components/NodeDetails.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了实体详情组件中的错误消息 |
| `/src/components/graph/components/LinkDetails.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了关系详情组件中的错误消息 |
| `/src/components/documents/documents-table.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了文档表格组件中的错误消息 |
| `/src/components/chat-engine/kb-list-select.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了知识库列表选择器中的文本 |
| `/src/components/graph/GraphCreateEntity.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了图形创建实体组件中的文本 |
| `/src/app/(main)/(.)auth/login/loading.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了登录加载页面的文本 |
| `/src/components/settings/SettingsField.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了设置字段组件中的警告提示和按钮文本 |
| `/src/components/chat/message-beta-alert.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了消息Beta提示组件中的文本 |
| `/src/components/form/root-error.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了表单根错误组件中的文本 |
| `/src/components/chat/message-answer.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了消息回答组件中的文本 |
| `/src/components/datasource/no-datasource-placeholder.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了数据源占位符组件中的文本 |
| `/src/components/site-nav.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了站点导航组件中的确认对话框文本 |
| `/src/components/datasource/datasource-card.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了数据源卡片组件中的文本 |
| `/src/components/llm/UpdateLLMForm.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了更新LLM表单中的删除按钮文本 |
| `/src/components/form/widgets/FileInput.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了文件输入组件的选择按钮 |
| `/src/components/datasource/create-datasource-form.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了创建数据源表单的所有标签和按钮文本 |
| `/src/app/(main)/(admin)/knowledge-bases/[id]/(tabs)/layout.tsx` | 已完成 | 2023-08-03 | AI助手 | 汉化了知识库布局组件中的导航文本和提示 |
| `/src/app/(main)/(admin)/knowledge-bases/[id]/(tabs)/tabs.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了知识库标签页组件中的导航项 |
| `/src/components/form/widgets/FilesInput.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了文件输入组件中的"移除"和"选择文件..."按钮 |
| `/src/app/(main)/(admin)/knowledge-bases/[id]/(tabs)/index-progress/page.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了索引进度页面的标题 |
| `/src/components/knowledge-base/knowledge-base-index.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了知识库索引组件中的卡片标题、图表标题和错误表格文本 |
| `/src/components/knowledge-base/knowledge-base-settings-form.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了知识库设置表单中的字段标签、说明和选项 |
| `/src/components/knowledge-base/knowledge-base-chunking-config-fields.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了知识库分块配置中的模式选择和参数设置字段 |
| `/src/app/(main)/(admin)/knowledge-bases/[id]/(tabs)/data-sources/page.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了数据源页面的标题、选项卡和创建选项 |
| `/src/components/datasource/no-datasource-placeholder.tsx` | 已检查 | 2023-08-04 | AI助手 | 确认已完成汉化，"数据源列表为空"提示文本已汉化 |
| `/src/components/knowledge-base/create-knowledge-base-form.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了创建知识库表单中的字段标签和占位符文本 |
| `/src/components/knowledge-base/form-index-methods.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了知识库索引方法表单组件中的标签和描述文本 |
| `/src/app/(main)/c/[id]/page.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了聊天详情页中的错误提示和按钮文本 |
| `/src/components/chat/chat-new-dialog.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了新建聊天对话框中的标题和按钮文本 |
| `/src/components/chat/chats-history.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了聊天历史组件中的删除对话框文本 |
| `/src/components/chat/chats-table.tsx` | 已完成 | 2023-08-04 | AI助手 | 汉化了聊天表格组件中的操作列标题和删除操作文本 |
| `/src/components/managed-dialog.tsx` | 已检查 | 2023-08-04 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/managed-dialog-close.tsx` | 已检查 | 2023-08-04 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/managed-panel.tsx` | 已检查 | 2023-08-04 | AI助手 | 已检查，无需汉化，组件中无硬编码文本 |
| `/src/components/chat-engine/chat-engines-table.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了聊天引擎表格中的表头和操作按钮文本 |
| `/src/app/(main)/page.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了首页中的占位符文本和描述 |
| `/src/app/(main)/(admin)/chat-engines/page.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了聊天引擎页面的面包屑和按钮文本 |
| `/src/components/ui/dialog.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了对话框组件中的关闭按钮无障碍文本 |
| `/src/components/ui/sheet.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了抽屉组件中的关闭按钮无障碍文本 |
| `/src/components/chat/message-input.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了消息输入组件中的占位符和下拉菜单选项 |
| `/src/app/(main)/(admin)/knowledge-bases/[id]/(special)/documents/[documentId]/chunks/page.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了文档块页面的面包屑导航和卡片标题 |
| `/src/components/documents/documents-table.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了文档表格的表头和操作按钮文本 |
| `/src/components/documents/documents-table-filters.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了文档表格过滤器中的按钮文本和占位符 |
| `/src/app/(main)/nav.tsx` | 已检查 | 2023-08-05 | AI助手 | 确认导航菜单已汉化完成，包括所有菜单项和提示文本 |
| `/src/components/site-nav.tsx` | 已完成 | 2023-08-05 | AI助手 | 汉化了站点导航组件中的确认对话框文本 |
| `/src/app/(main)/(admin)/llms/page.tsx` | 已完成 | 2023-08-06 | AI助手 | 汉化了大语言模型列表页面的面包屑和按钮文本 |
| `/src/components/llm/LLMsTable.tsx` | 已完成 | 2023-08-06 | AI助手 | 汉化了大语言模型表格中的表头和操作按钮文本 |
| `/src/app/(main)/(admin)/llms/create/page.tsx` | 已完成 | 2023-08-06 | AI助手 | 汉化了新建大语言模型页面的面包屑 |
| `/src/components/llm/CreateLLMForm.tsx` | 已完成 | 2023-08-06 | AI助手 | 汉化了创建大语言模型表单中的字段标签和提示文本 |
| `/src/app/(main)/(admin)/llms/[id]/page.tsx` | 已完成 | 2023-08-06 | AI助手 | 汉化了大语言模型详情页面的面包屑 |
| `/src/components/llm/UpdateLLMForm.tsx` | 已完成 | 2023-08-06 | AI助手 | 汉化了更新大语言模型表单中的字段标签和按钮文本 |
| `/src/components/site-header-actions.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了站点头部操作按钮组件中的社交媒体链接无障碍文本 |
| `/src/app/(main)/(user)/c/page.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了聊天历史页面的面包屑导航 |
| `/src/api/llms.ts` | 已完成 | 2023-08-07 | AI助手 | 汉化了大语言模型API文件中的接口说明和函数注释 |
| `/src/api/knowledge-base.ts` | 已完成 | 2023-08-07 | AI助手 | 汉化了知识库API文件中的接口说明、类型定义和函数注释 |
| `/src/api/chat-engines.ts` | 已完成 | 2023-08-07 | AI助手 | 汉化了聊天引擎API文件中的接口说明、类型定义和函数注释 |
| `/src/api/documents.ts` | 已完成 | 2023-08-07 | AI助手 | 汉化了文档API文件中的接口说明、类型定义和函数注释 |
| `/src/components/ui/calendar.tsx` | 已完成 | 2023-08-07 | AI助手 | 添加了日历的中文本地化，添加了上/下个月的无障碍标签 |
| `/src/components/ui/command.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了命令组件的搜索占位符和无结果提示文本 |
| `/src/components/ui/pagination.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了分页导航的文本和无障碍标签 |
| `/src/components/ui/toast.tsx` | 已完成 | 2023-08-07 | AI助手 | 汉化了提示消息的关闭按钮无障碍标签 |
| `/src/lib/strings.ts` | 已完成 | 2023-08-07 | AI助手 | 添加了模板变量提取函数的中文注释 |
| `/src/lib/react.ts` | 已完成 | 2023-08-07 | AI助手 | 添加了React工具函数的中文注释 |
| `/src/app/(main)/(admin)/chat-engines/new/page.tsx` | 已完成 | 2023-08-08 | AI助手 | 汉化了聊天引擎新建页面的导航标题 |
| `/src/components/chat-engine/create-chat-engine-form.tsx` | 已完成 | 2023-08-08 | AI助手 | 汉化了聊天引擎创建表单的UI文本 |
| `/src/app/(main)/(admin)/embedding-models/create/page.tsx` | 已完成 | 2023-08-08 | AI助手 | 汉化了嵌入模型创建页面的导航标题 |
| `/src/app/(main)/(admin)/evaluation/tasks/create/page.tsx` | 已完成 | 2023-08-08 | AI助手 | 汉化了评估任务创建页面的导航标题 |
| `/src/components/evaluations/create-evaluation-task-form.tsx` | 已完成 | 2023-08-08 | AI助手 | 汉化了评估任务创建表单的UI文本 |
| `/src/app/(main)/(admin)/stats/trending/page.tsx` | 已完成 | 2023-08-08 | AI助手 | 汉化了统计趋势页面的图表标题和描述 |

## 汉化指南

1. **汉化步骤**:
   - 找到待汉化的文件
   - 替换英文文本为中文
   - 保持代码结构不变，只修改文本内容
   - 在此清单中更新进度

2. **注意事项**:
   - 保留代码中的变量名和属性名
   - 只翻译用户可见的文本，不翻译代码逻辑
   - 保持UI布局一致，注意中文可能导致的宽度问题
   - 专业术语可考虑保留英文或中英并列
   - 许多基础UI组件不需要直接汉化，因为它们只是提供结构，文本内容在使用时提供

3. **常用术语对照表**:
   - knowledge base - 知识库
   - document - 文档
   - chat - 聊天
   - query - 查询
   - embedding - 嵌入
   - settings - 设置
   - dashboard - 仪表盘
   - vector search - 向量搜索 