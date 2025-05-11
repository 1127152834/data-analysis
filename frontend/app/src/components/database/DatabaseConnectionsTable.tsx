'use client';

import { 
  type DatabaseConnection, 
  getDatabaseConnections,
  deleteDatabaseConnection,
  testSavedDatabaseConnection,
  type ConnectionTestResponse
} from '@/api/database';
import { NextLink } from '@/components/nextjs/NextLink';
import { Badge } from '@/components/ui/badge';
import { actions } from '@/components/cells/actions';
import { DataTableRemote, type PageApiOptions } from '@/components/data-table-remote';
import { createColumnHelper } from '@tanstack/table-core';
import type { ColumnDef } from '@tanstack/react-table';
import { getErrorMessage } from '@/lib/errors';
import { toast } from 'sonner';
import { type Page, type PageParams } from '@/lib/request';

// 创建一个适配器函数，确保返回类型符合DataTableRemote的期望
const databaseConnectionsAdapter = async (
  page: PageParams, 
  options: PageApiOptions
): Promise<Page<DatabaseConnection>> => {
  const result = await getDatabaseConnections(page, options);
  // 确保结果是Page<DatabaseConnection>格式
  if (Array.isArray(result)) {
    // 如果返回的是数组，则将其转换为分页格式
    return {
      items: result,
      page: page.page || 1,
      size: page.size || 10,
      total: result.length,
      pages: Math.ceil(result.length / (page.size || 10)),
    };
  }
  // 如果已经是Page格式，则直接返回
  return result;
};

// 数据库连接列表组件
export function DatabaseConnectionsTable() {
  return (
    <DataTableRemote
      columns={columns}
      apiKey="api.database.connections.list"
      api={databaseConnectionsAdapter}
      idColumn="id"
    />
  );
}

const helper = createColumnHelper<DatabaseConnection>();
const columns: ColumnDef<DatabaseConnection, any>[] = [
  helper.accessor('name', {
    header: '名称',
    cell: ({ row }) => {
      const conn = row.original;
      return (
        <div>
          <div className="font-medium">{conn.name}</div>
          {conn.description && <div className="text-xs text-gray-500">{conn.description}</div>}
        </div>
      );
    },
  }),
  helper.accessor('database_type', {
    header: '类型',
    cell: ({ row }) => row.original.database_type,
  }),
  helper.accessor('connection_status', {
    header: '状态',
    cell: ({ row }) => {
      const status = row.original.connection_status;
      return (
        <Badge variant={status === 'connected' ? 'default' : status === 'error' ? 'destructive' : 'outline'}>
          {status}
        </Badge>
      );
    },
  }),
  helper.accessor('read_only', {
    header: '只读',
    cell: ({ row }) => row.original.read_only ? '是' : '否',
  }),
  helper.accessor('last_connected_at', {
    header: '最后连接时间',
    cell: ({ row }) => {
      const timestamp = row.original.last_connected_at;
      return timestamp ? new Date(timestamp).toLocaleString() : '-';
    },
  }),
  helper.display({
    id: 'operations',
    header: '操作',
    cell: actions(row => ([
      {
        key: 'edit',
        title: '编辑',
        action: async (context) => {
          context.router.push(`/database/${row.id}`);
          context.setDropdownOpen(false);
        },
      },
      {
        key: 'test',
        title: '测试连接',
        action: async (context) => {
          try {
            toast.promise(
              testSavedDatabaseConnection(row.id),
              {
                loading: `正在测试连接 "${row.name}"...`,
                success: (result: ConnectionTestResponse) => {
                  context.table.reload?.();
                  return `连接 "${row.name}" 测试成功: ${result.message || '连接正常'}`;
                },
                error: (err) => {
                  const errorMessage = err?.message || '测试连接时发生未知错误';
                  return `测试连接 "${row.name}" 失败: ${errorMessage}`;
                },
              }
            );
            context.setDropdownOpen(false);
          } catch (err) {
            console.error(`测试连接 "${row.name}" (ID: ${row.id}) 出错:`, err);
          }
        },
      },
      {
        key: 'delete',
        title: '删除',
        dangerous: {
          dialogTitle: '确认删除数据库连接',
          dialogDescription: `确定要删除数据库连接 "${row.name}" 吗？此操作无法撤销。`,
        },
        action: async (context) => {
          try {
            await deleteDatabaseConnection(row.id);
            context.table.reload?.();
            context.setDropdownOpen(false);
            toast.success(`数据库连接 "${row.name}" 已成功删除。`);
          } catch (err) {
            toast.error(`删除数据库连接 "${row.name}" 失败`, {
              description: getErrorMessage(err),
            });
            throw err;
          }
        },
      },
    ])),
  }),
]; 