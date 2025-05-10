import { AdminPageHeading } from '@/components/admin-page-heading';
import { FeedbacksTable } from '@/components/feedbacks/feedbacks-table';

export default function ChatEnginesPage () {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '反馈' },
        ]}
      />
      <FeedbacksTable />
    </>
  );
}
