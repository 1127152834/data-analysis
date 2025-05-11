'use client';

import { AdminPageHeading } from '@/components/admin-page-heading';
import { CreateDatabaseConnectionForm } from '@/components/database/CreateDatabaseConnectionForm';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';

export default function Page() {
  const router = useRouter();
  const [transitioning, startTransition] = useTransition();

  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '数据源管理', url: '/database' }, 
          { title: '数据库连接', url: '/database' }, // 父级也链接到列表页
          { title: '创建连接' },
        ]}
      />
      <div className="mt-6">
        <CreateDatabaseConnectionForm
          transitioning={transitioning}
          onCreated={newConnection => {
            startTransition(() => {
              // 创建成功后，可以跳转到新连接的编辑页面或列表页面
              // 这里我们跳转到编辑页 (假设有编辑页)
              router.push(`/database/${newConnection.id}`);
              // 或者跳转回列表页并刷新数据
              // router.push('/database'); 
              router.refresh(); // 确保数据刷新
            });
          }}
        />
      </div>
    </>
  );
} 
 