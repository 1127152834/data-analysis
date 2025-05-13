import { AdminPageHeading } from '@/components/admin-page-heading';
import { EvaluationDatasetsTable } from '@/components/evaluations/evaluation-datasets-table';
import { NextLink } from '@/components/nextjs/NextLink';

export default function EvaluationDatasetsPage () {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '评估', docsUrl: 'https://autoflow.tidb.ai/evaluation' },
          { title: '数据集' },
        ]}
      />
      <NextLink href="/evaluation/datasets/create">新建评估数据集</NextLink>
      <EvaluationDatasetsTable />
    </>
  );
}
