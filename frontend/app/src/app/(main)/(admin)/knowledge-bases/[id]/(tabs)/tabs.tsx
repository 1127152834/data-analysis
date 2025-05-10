'use client';

import { useKnowledgeBase } from '@/components/knowledge-base/hooks';
import { SecondaryNavigatorLink } from '@/components/secondary-navigator-list';

export function KnowledgeBaseTabs ({ knowledgeBaseId }: { knowledgeBaseId: number }) {
  const { knowledgeBase } = useKnowledgeBase(knowledgeBaseId);

  return (
    <>
      <SecondaryNavigatorLink pathname={`/knowledge-bases/${knowledgeBaseId}`}>
        文档
        <span className="ml-auto text-xs font-normal text-muted-foreground">
          {knowledgeBase?.documents_total}
        </span>
      </SecondaryNavigatorLink>
      <SecondaryNavigatorLink pathname={`/knowledge-bases/${knowledgeBaseId}/data-sources`}>
        数据源
        <span className="ml-auto text-xs font-normal text-muted-foreground">
          {knowledgeBase?.data_sources_total}
        </span>
      </SecondaryNavigatorLink>
      <SecondaryNavigatorLink pathname={`/knowledge-bases/${knowledgeBaseId}/index-progress`}>
        索引进度
      </SecondaryNavigatorLink>
      {/*<TabsTrigger*/}
      {/*  disabled={true}*/}
      {/*  value="retrieval-tester"*/}
      {/*  onClick={() => startTransition(() => {*/}
      {/*    router.push(`/knowledge-bases/${knowledgeBase.id}/retrieval-tester`);*/}
      {/*  })}*/}
      {/*>*/}
      {/*  Retrieval Tester*/}
      {/*</TabsTrigger>*/}
      <SecondaryNavigatorLink pathname={`/knowledge-bases/${knowledgeBaseId}/knowledge-graph-explorer`}>
        知识图谱
      </SecondaryNavigatorLink>
      <SecondaryNavigatorLink pathname={`/knowledge-bases/${knowledgeBaseId}/settings`}>
        设置
      </SecondaryNavigatorLink>
    </>
  );
}