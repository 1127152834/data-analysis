import { AdminPageHeading } from '@/components/admin-page-heading';
import { NextLink } from '@/components/nextjs/NextLink';
import { PlusIcon } from 'lucide-react';
import RerankerModelsTable from '@/components/reranker/RerankerModelsTable';

export default function Page () {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '模型' },
          { title: '重排序模型', docsUrl: 'https://autoflow.tidb.ai/reranker-model' },
        ]}
      />
      <NextLink href="/reranker-models/create">
        <PlusIcon className="size-4" />
        创建重排序模型
      </NextLink>
      <RerankerModelsTable />
    </>
  );
}
