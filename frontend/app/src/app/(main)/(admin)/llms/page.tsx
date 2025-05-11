import { AdminPageHeading } from '@/components/admin-page-heading';
import { LLMsTable } from '@/components/llm/LLMsTable';
import { NextLink } from '@/components/nextjs/NextLink';
import { PlusIcon } from 'lucide-react';

export default function Page () {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '模型' },
          { title: '大语言模型', docsUrl: 'https://autoflow.tidb.ai/llm' },
        ]}
      />
      <NextLink href="/llms/create">
        <PlusIcon className="size-4" />
        创建大语言模型
      </NextLink>
      <LLMsTable />
    </>
  );
}
