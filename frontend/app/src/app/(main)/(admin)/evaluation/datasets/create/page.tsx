'use client';

import { AdminPageHeading } from '@/components/admin-page-heading';
import { CreateEvaluationDatasetForm } from '@/components/evaluations/create-evaluation-dataset-form';
import { mutateEvaluationDatasets } from '@/components/evaluations/hooks';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';

export default function EvaluationTaskPage () {
  const [transitioning, startTransition] = useTransition();
  const router = useRouter();

  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '评估', docsUrl: 'https://autoflow.tidb.ai/evaluation' },
          { title: '数据集', url: '/evaluation/datasets' },
          { title: '创建' },
        ]}
      />
      <CreateEvaluationDatasetForm
        transitioning={transitioning}
        onCreated={evaluationDataset => {
          void mutateEvaluationDatasets();
          startTransition(() => {
            router.push(`/evaluation/datasets/${evaluationDataset.id}`);
            router.refresh();
          });
        }}
      />
    </>
  );
}
