'use client'; // 标记为客户端组件

import { useEffect, useState, useTransition } from 'react';
import { getDatabaseConnection, DatabaseConnection } from '@/api/database';
import { AdminPageHeading } from '@/components/admin-page-heading';
import { UpdateDatabaseConnectionForm } from '@/components/database/UpdateDatabaseConnectionForm';
import { useRouter } from 'next/navigation'; // For router.refresh()
import { toast } from 'sonner'; // Assuming Sonner for toast notifications

// 定义组件参数类型
interface DatabaseConnectionDetailProps {
  connectionId: string;
}

// 客户端组件，通过props接收ID
export function DatabaseConnectionDetail({ connectionId }: DatabaseConnectionDetailProps) {
  const router = useRouter();
  const [connection, setConnection] = useState<DatabaseConnection | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isTransitioning, startTransition] = useTransition(); // For form

  useEffect(() => {
    if (!connectionId) {
      setError('无效的连接ID');
      setIsLoading(false);
      return;
    }

    const parsedId = parseInt(connectionId, 10);
    if (isNaN(parsedId)) {
      setError('无效的连接ID');
      setIsLoading(false);
      return;
    }

    async function fetchData(id: number) {
      setIsLoading(true);
      setError(null);
      try {
        const data = await getDatabaseConnection(id);
        if (data) {
          setConnection(data);
        } else {
          setError('数据库连接未找到');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取连接详情失败');
        console.error(err);
      }
      setIsLoading(false);
    }

    fetchData(parsedId);
  }, [connectionId]);

  const handleUpdated = (updatedConnection: DatabaseConnection) => {
    toast.success(`数据库连接 "${updatedConnection.name}" 已成功更新!`);
    // Option 1: Update local state if the API returns the full updated object
    setConnection(updatedConnection);
    // Option 2: Or simply refresh server components to re-fetch data
    startTransition(() => {
        router.refresh();
    });
    // Option 3: Could also navigate away, e.g., back to the list
    // router.push('/database');
  };

  if (isLoading) {
    return (
      <>
        <AdminPageHeading breadcrumbs={[{ title: '数据源管理' }, { title: '数据库连接'}, {title: '加载中...'}]} />
        <p className="mt-6">正在加载连接信息...</p>
      </>
    );
  }

  if (error) {
    return (
      <>
        <AdminPageHeading breadcrumbs={[{ title: '数据源管理' }, { title: '数据库连接'}, {title: '错误'}]} />
        <p className="mt-6 text-red-500">错误: {error}</p>
      </>
    );
  }

  if (!connection) {
    // This case should ideally be covered by error state if ID was valid but not found
    // Or if ID was invalid from the start.
    return (
        <>
            <AdminPageHeading breadcrumbs={[{ title: '数据源管理' }, { title: '数据库连接'}, {title: '未找到'}]} />
            <p className="mt-6">无法加载连接信息。</p>
        </>
    );
  }

  return (
    <>
      <AdminPageHeading
        breadcrumbs={[
          { title: '数据源管理', url: '/database' },
          { title: '数据库连接', url: '/database' },
          { title: connection.name }, // Dynamic name
        ]}
      />
      <div className="mt-6">
        <UpdateDatabaseConnectionForm 
            connection={connection} 
            onUpdated={handleUpdated} 
            transitioning={isTransitioning} 
        />
      </div>
    </>
  );
} 