'use client';

import { AdminPageHeading } from '@/components/admin-page-heading';
import { CreateKnowledgeBaseForm } from '@/components/knowledge-base/create-knowledge-base-form';

export default function NewKnowledgeBasePage () {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '知识库', url: '/knowledge-bases' },
          { title: 'New' },
        ]}
      />
      <CreateKnowledgeBaseForm />
    </>
  );
}
