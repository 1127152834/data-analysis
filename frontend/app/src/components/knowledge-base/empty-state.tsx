import { LibraryBig } from 'lucide-react';

export default function KnowledgeBaseEmptyState () {
  return (
    <div className="flex flex-col items-center justify-center h-[50vh] gap-6 rounded-md">
      <div className="flex items-center justify-center w-20 h-20 rounded-full bg-gray-200 dark:bg-gray-800">
        <LibraryBig size={40} />
      </div>
      <div className="space-y-2 text-center">
        <h2 className="text-2xl font-bold tracking-tight">暂无知识库可显示</h2>
        <p className="text-gray-500 dark:text-gray-400">
          要使AI助手生成更准确的回答，请按照以下步骤操作:
        </p>
        <p className="text-gray-500 dark:text-gray-400">
          1. 创建知识库 -&gt;
          2. 导入特定领域的文档 -&gt;
          3. 将知识库关联到聊天引擎
        </p>
      </div>
    </div>
  );
}