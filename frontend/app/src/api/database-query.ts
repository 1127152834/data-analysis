import { authenticationHeaders, handleErrors, handleResponse, type Page, type PageParams, requestUrl, zodPage } from '@/lib/request';
import { zodJsonDate } from '@/lib/zod';
import { z } from 'zod';

// 数据库查询历史记录接口定义
export interface DatabaseQueryHistory {
  id: number;
  chat_id: string;
  connection_name: string;
  database_type: string;
  question: string;
  query: string;
  is_successful: boolean;
  result_summary: Record<string, any>;
  result_sample: Record<string, any>[];
  execution_time_ms: number;
  rows_returned: number;
  user_feedback?: number;
  feedback_comments?: string;
  executed_at: Date;
}

// 反馈请求参数定义
export interface QueryFeedbackRequest {
  feedback_score: number;  // 1-5 分
  feedback_comments?: string;
}

// 查询统计信息接口定义
export interface QueryStatistics {
  total_queries: number;
  successful_queries: number;
  success_rate: number;
  databases_used: Array<{
    name: string;
    query_count: number;
  }>;
}

// Schema 定义
const databaseQueryHistorySchema = z.object({
  id: z.number(),
  chat_id: z.string(),
  connection_name: z.string(),
  database_type: z.string(),
  question: z.string(),
  query: z.string(),
  is_successful: z.boolean(),
  result_summary: z.record(z.unknown()),
  result_sample: z.array(z.record(z.unknown())),
  execution_time_ms: z.number(),
  rows_returned: z.number(),
  user_feedback: z.number().optional(),
  feedback_comments: z.string().optional(),
  executed_at: zodJsonDate(),
});

const queryStatisticsSchema = z.object({
  total_queries: z.number(),
  successful_queries: z.number(),
  success_rate: z.number(),
  databases_used: z.array(
    z.object({
      name: z.string(),
      query_count: z.number(),
    })
  ),
});

/**
 * 获取指定聊天的数据库查询历史
 */
export async function getChatDatabaseQueries(
  chatId: string,
  { page = 1, size = 20 }: PageParams = {}
): Promise<Page<DatabaseQueryHistory>> {
  return await fetch(
    requestUrl(`/api/v1/chats/${chatId}/database/queries`, { page, size }),
    {
      headers: await authenticationHeaders(),
    }
  ).then(handleResponse(zodPage(databaseQueryHistorySchema)));
}

/**
 * 获取用户最近的数据库查询记录
 */
export async function getRecentDatabaseQueries(
  { page = 1, size = 20 }: PageParams = {}
): Promise<Page<DatabaseQueryHistory>> {
  return await fetch(
    requestUrl('/api/v1/database/queries/recent', { page, size }),
    {
      headers: await authenticationHeaders(),
    }
  ).then(handleResponse(zodPage(databaseQueryHistorySchema)));
}

/**
 * 获取指定聊天的数据库查询统计信息
 */
export async function getChatDatabaseStatistics(
  chatId: string
): Promise<QueryStatistics> {
  return await fetch(
    requestUrl(`/api/v1/chats/${chatId}/database/statistics`),
    {
      headers: await authenticationHeaders(),
    }
  ).then(handleResponse(queryStatisticsSchema));
}

/**
 * 提交数据库查询反馈
 */
export async function submitQueryFeedback(
  queryId: number,
  feedback: QueryFeedbackRequest
): Promise<void> {
  await fetch(
    requestUrl(`/api/v1/database/queries/${queryId}/feedback`),
    {
      method: 'PUT',
      headers: {
        ...await authenticationHeaders(),
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(feedback),
    }
  ).then(handleErrors);
} 