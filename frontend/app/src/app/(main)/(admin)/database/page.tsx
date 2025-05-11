import { AdminPageHeading } from '@/components/admin-page-heading';
import { DatabaseConnectionsTable } from '@/components/database/DatabaseConnectionsTable';
import { NextLink } from '@/components/nextjs/NextLink';
import { PlusIcon } from 'lucide-react';

// 数据库连接列表页面
export default function Page() {
  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '数据源管理' }, // Top-level, consider if there's a parent category like 'Settings' or 'Integrations'
          { title: '数据库连接', docsUrl: '' }, // Add relevant docs URL later
        ]}
      />
      <div className="my-4">
        <NextLink href="/database/create" className="inline-flex items-center gap-1 rounded-md bg-primary px-3 py-2 text-sm text-primary-foreground hover:bg-primary/90">
          <PlusIcon className="size-4" />
          创建数据库连接
        </NextLink>
      </div>
      <DatabaseConnectionsTable />
    </>
  );
} 
 