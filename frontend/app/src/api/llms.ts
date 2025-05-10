import { type ProviderOption, providerOptionSchema } from '@/api/providers';
import { authenticationHeaders, handleErrors, handleResponse, type Page, type PageParams, requestUrl, zodPage } from '@/lib/request';
import { zodJsonDate } from '@/lib/zod';
import { z, type ZodType, type ZodTypeDef } from 'zod';

/**
 * 大语言模型摘要信息接口
 */
export interface LLMSummary {
  id: number;
  name: string;
  provider: string;
  model: string;
  is_default: boolean;
}

/**
 * 大语言模型完整信息接口，继承自LLMSummary
 */
export interface LLM extends LLMSummary {
  config?: any;
  created_at: Date | null;
  updated_at: Date | null;
}

/**
 * 大语言模型选项接口，继承自ProviderOption
 */
export interface LlmOption extends ProviderOption {
  default_llm_model: string;
  llm_model_description: string;
}

/**
 * 创建大语言模型所需参数接口
 */
export interface CreateLLM {
  name: string;
  provider: string;
  model: string;
  config?: any;
  is_default?: boolean;
  credentials: string | object;
}

/**
 * 更新大语言模型所需参数接口
 */
export interface UpdateLLM {
  name?: string;
  config?: any;
  credentials?: string | object;
}

// Zod验证模式定义
export const llmSummarySchema = z.object({
  id: z.number(),
  name: z.string(),
  provider: z.string(),
  model: z.string(),
  is_default: z.boolean(),
}) satisfies ZodType<LLMSummary, ZodTypeDef, any>;

const llmSchema = llmSummarySchema.extend({
  config: z.any(),
  created_at: zodJsonDate().nullable(),
  updated_at: zodJsonDate().nullable(),
}) satisfies ZodType<LLM, ZodTypeDef, any>;

const llmOptionSchema = providerOptionSchema.and(z.object({
  default_llm_model: z.string(),
  llm_model_description: z.string(),
})) satisfies ZodType<LlmOption, any, any>;

/**
 * 获取大语言模型提供商选项列表
 * @returns 返回Promise，包含大语言模型选项数组
 */
export async function listLlmOptions () {
  return await fetch(requestUrl(`/api/v1/admin/llms/providers/options`), {
    headers: {
      ...await authenticationHeaders(),
    },
  })
    .then(handleResponse(llmOptionSchema.array()));
}

/**
 * 获取大语言模型列表
 * @param 分页参数对象，包含page和size
 * @returns 返回Promise，包含分页的大语言模型列表
 */
export async function listLlms ({ page = 1, size = 10 }: PageParams = {}): Promise<Page<LLM>> {
  return await fetch(requestUrl('/api/v1/admin/llms', { page, size }), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(zodPage(llmSchema)));
}

/**
 * 获取指定ID的大语言模型详情
 * @param id 大语言模型ID
 * @returns 返回Promise，包含大语言模型详情
 */
export async function getLlm (id: number): Promise<LLM> {
  return await fetch(requestUrl(`/api/v1/admin/llms/${id}`), {
    headers: await authenticationHeaders(),
  }).then(handleResponse(llmSchema));
}

/**
 * 创建新的大语言模型
 * @param create 创建大语言模型所需的参数
 * @returns 返回Promise，包含创建成功的大语言模型信息
 */
export async function createLlm (create: CreateLLM) {
  return await fetch(requestUrl(`/api/v1/admin/llms`), {
    method: 'POST',
    body: JSON.stringify(create),
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
  }).then(handleResponse(llmSchema));
}

/**
 * 更新指定ID的大语言模型
 * @param id 大语言模型ID
 * @param update 更新大语言模型所需的参数
 * @returns 返回Promise，包含更新后的大语言模型信息
 */
export async function updateLlm (id: number, update: UpdateLLM) {
  return await fetch(requestUrl(`/api/v1/admin/llms/${id}`), {
    method: 'PUT',
    body: JSON.stringify(update),
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
  }).then(handleResponse(llmSchema));
}

/**
 * 删除指定ID的大语言模型
 * @param id 大语言模型ID
 */
export async function deleteLlm (id: number) {
  await fetch(requestUrl(`/api/v1/admin/llms/${id}`), {
    method: 'DELETE',
    headers: await authenticationHeaders(),
  }).then(handleErrors);
}

/**
 * 测试大语言模型配置是否有效
 * @param createLLM 创建大语言模型所需的参数
 * @returns 返回Promise，包含测试结果和可能的错误信息
 */
export async function testLlm (createLLM: CreateLLM) {
  return await fetch(requestUrl(`/api/v1/admin/llms/test`), {
    method: 'POST',
    body: JSON.stringify(createLLM),
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
  })
    .then(handleResponse(z.object({
      success: z.boolean(),
      error: z.string().optional(),
    })));
}
