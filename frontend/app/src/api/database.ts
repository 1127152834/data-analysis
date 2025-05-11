// 定义数据库连接相关的类型和Schema
import { authenticationHeaders, handleErrors, handleResponse, requestUrl, type Page, type PageParams, zodPage } from '@/lib/request';
import { z } from 'zod';

/**
 * 支持的数据库类型
 * 与后端 app/models/database_connection.py 中的 DatabaseType 枚举对应
 */
export type DatabaseConnectionType = 'mysql' | 'postgresql' | 'mongodb' | 'sql_server' | 'oracle';

/**
 * 数据库连接状态
 * 与后端 app/models/database_connection.py 中的 ConnectionStatus 枚举对应
 */
export type DatabaseConnectionStatus = 'connected' | 'disconnected' | 'error';

// Zod Schema 定义
export const databaseConnectionTypeSchema = z.enum(['mysql', 'postgresql', 'mongodb', 'sql_server', 'oracle']);
export const databaseConnectionStatusSchema = z.enum(['connected', 'disconnected', 'error']);

// 数据库连接对象Schema
export const databaseConnectionSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().optional(),
  database_type: databaseConnectionTypeSchema,
  config: z.record(z.any()), // 具体的配置结构取决于数据库类型
  read_only: z.boolean(),
  connection_status: databaseConnectionStatusSchema,
  last_connected_at: z.string().optional(),
  metadata_cache: z.record(z.any()).optional(),
  metadata_updated_at: z.string().nullable().optional(),
  metadata_summary: z.record(z.any()).optional(),
});

// 创建数据库连接的Schema
export const databaseConnectionCreatePayloadSchema = z.object({
  name: z.string().min(1, "名称不能为空"),
  description: z.string().optional(),
  database_type: databaseConnectionTypeSchema,
  config: z.record(z.any()),
  read_only: z.boolean().optional().default(true),
  test_connection: z.boolean().optional().default(false),
});

// 更新数据库连接的Schema
export const databaseConnectionUpdatePayloadSchema = z.object({
  name: z.string().min(1, "名称不能为空").optional(),
  description: z.string().optional(),
  database_type: databaseConnectionTypeSchema.optional(),
  config: z.record(z.any()).optional(),
  read_only: z.boolean().optional(),
  test_connection: z.boolean().optional().default(false),
});

// 连接测试响应的Schema
export const connectionTestResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  details: z.record(z.any()).nullable().optional(),
});

// 接口定义 - 基于Schema的类型
export type DatabaseConnection = z.infer<typeof databaseConnectionSchema>;
export type DatabaseConnectionCreatePayload = z.infer<typeof databaseConnectionCreatePayloadSchema>;
export type DatabaseConnectionUpdatePayload = z.infer<typeof databaseConnectionUpdatePayloadSchema>;
export type ConnectionTestResponse = z.infer<typeof connectionTestResponseSchema>;

// API 函数

/**
 * 获取支持的数据库类型列表
 */
export async function getDatabaseTypes(): Promise<Array<{ value: DatabaseConnectionType, label: string }>> {
  const types = await fetch(requestUrl('/api/v1/admin/database/types'), {
    headers: await authenticationHeaders(),
  }).then(handleResponse(z.array(databaseConnectionTypeSchema)));
  
  return types.map(type => ({
    value: type,
    // Simple capitalization for label, can be more sophisticated if needed
    label: type.charAt(0).toUpperCase() + type.slice(1), 
  }));
}

/**
 * 获取所有数据库连接，支持分页
 */
export interface GetDatabaseConnectionsParams {
  query?: string;
  database_type?: DatabaseConnectionType;
  connection_status?: DatabaseConnectionStatus;
  skip?: number;
  limit?: number;
}

export async function getDatabaseConnections(params?: GetDatabaseConnectionsParams | PageParams, options?: { globalFilter: string }): Promise<DatabaseConnection[] | Page<DatabaseConnection>> {
  // 处理DataTableRemote传入的分页参数
  const queryParams: Record<string, string> = {};
  
  if (params) {
    if ('page' in params) {
      // DataTableRemote格式
      queryParams.skip = String(((params.page || 1) - 1) * (params.size || 10));
      queryParams.limit = String(params.size || 10);
      if (options?.globalFilter) {
        queryParams.query = options.globalFilter;
      }
    } else {
      // 原始格式
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined) {
          queryParams[key] = String(value);
        }
      });
    }
  }

  const data = await fetch(requestUrl('/api/v1/admin/database/connections', queryParams), {
    headers: await authenticationHeaders(),
  }).then(handleResponse(z.array(databaseConnectionSchema)));

  // 如果是DataTableRemote调用，转换为分页格式
  if (params && 'page' in params) {
    return {
      items: data,
      page: params.page || 1,
      size: params.size || 10,
      total: data.length, // 注意：后端API可能需要提供实际总数
      pages: Math.ceil(data.length / (params.size || 10)), // 暂时基于当前数据计算
    };
  }

  return data;
}

/**
 * 创建一个新的数据库连接
 * @param payload 创建连接所需的数据
 */
export async function createDatabaseConnection(payload: DatabaseConnectionCreatePayload): Promise<DatabaseConnection> {
  return fetch(requestUrl('/api/v1/admin/database/connections'), {
    method: 'POST',
    headers: {
      ...await authenticationHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  }).then(handleResponse(databaseConnectionSchema));
}

/**
 * 获取指定ID的数据库连接详情
 * @param id 数据库连接ID
 */
export async function getDatabaseConnection(id: number): Promise<DatabaseConnection | null> {
  try {
    return await fetch(requestUrl(`/api/v1/admin/database/connections/${id}`), {
      headers: await authenticationHeaders(),
    }).then(handleResponse(databaseConnectionSchema));
  } catch (error) {
    if (error instanceof Error && error.message.includes('404')) {
      console.warn(`Database connection with ID ${id} not found.`);
      return null;
    }
    throw error;
  }
}

/**
 * 更新指定ID的数据库连接
 * @param id 数据库连接ID
 * @param payload 更新连接所需的数据
 */
export async function updateDatabaseConnection(id: number, payload: DatabaseConnectionUpdatePayload): Promise<DatabaseConnection> {
  console.log("Sending payload to update database connection:", JSON.stringify(payload));
  
  return fetch(requestUrl(`/api/v1/admin/database/connections/${id}`), {
    method: 'PUT',
    headers: {
      ...await authenticationHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ connection_update: payload }),
  }).then(handleResponse(databaseConnectionSchema));
}

/**
 * 删除指定ID的数据库连接
 * @param id 数据库连接ID
 */
export async function deleteDatabaseConnection(id: number): Promise<void> {
  await fetch(requestUrl(`/api/v1/admin/database/connections/${id}`), {
    method: 'DELETE',
    headers: await authenticationHeaders(),
  }).then(handleErrors);
}

/**
 * 测试数据库连接配置 (针对未保存的配置)
 * @param config 数据库连接配置
 */
export async function testDatabaseConnection(config: DatabaseConnectionCreatePayload): Promise<ConnectionTestResponse> {
  // TODO: 实现API调用 - 这需要后端支持一个测试未保存配置的端点
  console.warn('testDatabaseConnection (for unsaved config) is not yet implemented pending backend endpoint. Returning mocked success.', config);
  return Promise.resolve({ success: true, message: 'Connection test successful (mocked for unsaved config)' });
}

/**
 * 测试已保存的数据库连接
 * @param connectionId 要测试的数据库连接ID
 */
export async function testSavedDatabaseConnection(connectionId: number): Promise<ConnectionTestResponse> {
  return fetch(requestUrl(`/api/v1/admin/database/connections/${connectionId}/test`), {
    method: 'POST',
    headers: await authenticationHeaders(),
  }).then(handleResponse(connectionTestResponseSchema));
} 