'use client';

import { AdminPageHeading } from '@/components/admin-page-heading';
import { EmbeddingModelsTable } from '@/components/embedding-models/EmbeddingModelsTable';
import { NextLink } from '@/components/nextjs/NextLink';
import { PlusIcon } from 'lucide-react';

export default function EmbeddingModelPage () {

  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '模型' },
          { title: '向量模型', docsUrl: 'https://autoflow.tidb.ai/embedding-model' },
        ]}
      />
      <NextLink href="/embedding-models/create">
        <PlusIcon className="size-4" />
        创建向量模型
      </NextLink>
      <EmbeddingModelsTable />
    </>
  );
}
