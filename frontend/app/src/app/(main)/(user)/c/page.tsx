import { AdminPageHeading } from '@/components/admin-page-heading';
import { ChatsTable } from '@/components/chat/chats-table';
import { requireAuth } from '@/lib/auth';

export default async function ConversationsListPage () {
  await requireAuth();

  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '聊天历史' },
        ]}
      />
      <ChatsTable />
    </>
  );
}

export const dynamic = 'force-dynamic';
