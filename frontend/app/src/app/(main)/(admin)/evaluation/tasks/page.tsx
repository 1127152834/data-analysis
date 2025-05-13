import { AdminPageHeading } from '@/components/admin-page-heading';
import { EvaluationTasksTable } from '@/components/evaluations/evaluation-tasks-table';
import { NextLink } from '@/components/nextjs/NextLink';

export default function EvaluationTasksPage () {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '评估', docsUrl: 'https://autoflow.tidb.ai/evaluation' },
          { title: '任务' },
        ]}
      />
      <NextLink href="/evaluation/tasks/create">新建评估任务</NextLink>
      <EvaluationTasksTable />
    </>
  );
}
