// 定义数据库连接相关的类型和Schema
import { authenticationHeaders, handleErrors, handleResponse, requestUrl, type Page, type PageParams, zodPage } from '@/lib/request';
import { z } from 'zod';

/**
 * 支持的数据库类型
 * 与后端 app/models/database_connection.py 中的 DatabaseType 枚举对应
 */
export type DatabaseConnectionType = 'mysql' | 'postgresql' | 'mongodb' | 'sqlserver' | 'oracle' | 'sqlite';

/**
 * 数据库连接状态
 * 与后端 app/models/database_connection.py 中的 ConnectionStatus 枚举对应
 */
export type DatabaseConnectionStatus = 'connected' | 'disconnected' | 'error';

/**
 * 数据库访问角色
 */
export type DatabaseAccessRole = 'admin' | 'user';

// Zod Schema 定义
export const databaseConnectionTypeSchema = z.enum(['mysql', 'postgresql', 'mongodb', 'sqlserver', 'oracle', 'sqlite']);
export const databaseConnectionStatusSchema = z.enum(['connected', 'disconnected', 'error']);
export const databaseAccessRoleSchema = z.enum(['admin', 'user']);

// 数据库连接对象Schema
export const databaseConnectionSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().optional(),
  database_type: databaseConnectionTypeSchema,
  config: z.record(z.any()), // 具体的配置结构取决于数据库类型
  read_only: z.boolean(),
  connection_status: databaseConnectionStatusSchema,
  last_connected_at: z.string().nullable().optional(),
  metadata_cache: z.record(z.any()).optional(),
  metadata_updated_at: z.string().nullable().optional(),
  metadata_summary: z.record(z.any()).optional(),
  // 添加表描述、列描述和权限配置相关字段
  table_descriptions: z.record(z.string()).optional(),
  column_descriptions: z.record(z.string()).optional(),
  accessible_roles: z.array(databaseAccessRoleSchema).optional().default(['admin']),
});

// 创建数据库连接的Schema
export const databaseConnectionCreatePayloadSchema = z.object({
  name: z.string().min(1, "名称不能为空"),
  description: z.string().min(1, "描述不能为空"),
  database_type: databaseConnectionTypeSchema,
  config: z.record(z.any()),
  read_only: z.boolean().optional().default(true),
  test_connection: z.boolean().optional().default(false),
  // 添加表描述、列描述和权限配置相关字段
  table_descriptions: z.record(z.string()).optional(),
  column_descriptions: z.record(z.string()).optional(),
  accessible_roles: z.array(databaseAccessRoleSchema).optional(),
});

// 更新数据库连接的Schema
export const databaseConnectionUpdatePayloadSchema = z.object({
  name: z.string().min(1, "名称不能为空").optional(),
  description: z.string().optional(),
  database_type: databaseConnectionTypeSchema.optional(),
  config: z.record(z.any()).optional(),
  read_only: z.boolean().optional(),
  test_connection: z.boolean().optional().default(false),
  // 添加表描述、列描述和权限配置相关字段
  table_descriptions: z.record(z.string()).optional(),
  column_descriptions: z.record(z.string()).optional(),
  accessible_roles: z.array(databaseAccessRoleSchema).optional(),
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
    body: JSON.stringify({ connection_create: payload }),
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
  // 打印原始payload进行调试
  console.log("原始更新payload:", payload);
  
  // 确保test_connection字段存在
  const finalPayload = {
    ...payload,
    test_connection: payload.test_connection !== undefined ? payload.test_connection : false
  };
  
  // 打印最终发送的payload
  console.log("发送到后端的最终payload:", JSON.stringify({
    connection_update: finalPayload
  }, null, 2));
  
  try {
    const response = await fetch(requestUrl(`/api/v1/admin/database/connections/${id}`), {
    method: 'PUT',
    headers: {
      ...await authenticationHeaders(),
      'Content-Type': 'application/json',
    },
      body: JSON.stringify({ connection_update: finalPayload }),
    });
    
    // 尝试获取原始响应文本进行调试
    const responseClone = response.clone();
    const responseText = await responseClone.text();
    console.log(`更新数据库连接 ID=${id} 响应:`, responseText);
    
    // 继续正常处理
    return handleResponse(databaseConnectionSchema)(response);
  } catch (error) {
    console.error("更新数据库连接出错:", error);
    throw error;
  }
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
export async function testDatabaseConfig(config: DatabaseConnectionCreatePayload): Promise<ConnectionTestResponse> {
  console.log("Testing database connection config:", JSON.stringify(config));
  
  return fetch(requestUrl('/api/v1/admin/database/connections/test-config'), {
    method: 'POST',
    headers: {
      ...await authenticationHeaders(),
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ connection_config: config }),
  }).then(handleResponse(connectionTestResponseSchema));
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

/**
 * 上传SQLite数据库文件
 * @param file 要上传的SQLite数据库文件
 */
export async function uploadSQLiteFile(file: File): Promise<{ filename: string; relative_path: string }> {
  const formData = new FormData();
  formData.append('file', file);
  
  return fetch(requestUrl('/api/v1/admin/database/sqlite-upload'), {
    method: 'POST',
    headers: await authenticationHeaders(),
    body: formData,
  }).then(handleResponse(z.object({
    filename: z.string(),
    original_filename: z.string(),
    file_path: z.string(),
    relative_path: z.string()
  })));
} 