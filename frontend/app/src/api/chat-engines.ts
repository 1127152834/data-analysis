import { authenticationHeaders, handleErrors, handleResponse, type Page, type PageParams, requestUrl, zodPage } from '@/lib/request';
import { zodJsonDate } from '@/lib/zod';
import { z, type ZodType } from 'zod';

/**
 * 聊天引擎接口
 */
export interface ChatEngine {
  id: number;                      // 聊天引擎ID
  name: string;                    // 聊天引擎名称
  updated_at: Date;                // 更新时间
  created_at: Date;                // 创建时间
  deleted_at: Date | null;         // 删除时间
  engine_options: ChatEngineOptions; // 引擎选项
  llm_id: number | null;           // 大语言模型ID
  fast_llm_id: number | null;      // 快速大语言模型ID
  reranker_id: number | null;      // 重排序模型ID
  is_default: boolean;             // 是否为默认引擎
}

/**
 * 创建聊天引擎所需参数接口
 */
export interface CreateChatEngineParams {
  name: string;                    // 聊天引擎名称
  engine_options: ChatEngineOptions; // 引擎选项
  llm_id?: number | null;          // 大语言模型ID
  fast_llm_id?: number | null;     // 快速大语言模型ID
  reranker_id?: number | null;     // 重排序模型ID
}

/**
 * 聊天引擎选项接口
 */
export interface ChatEngineOptions {
  external_engine_config?: {        // 外部引擎配置
    stream_chat_api_url?: string | null // 流式聊天API地址
  } | null;
  clarify_question?: boolean | null;    // 是否澄清问题
  further_questions?: boolean | null;   // 是否提供后续问题
  knowledge_base?: ChatEngineKnowledgeBaseOptions | null; // 知识库选项
  knowledge_graph?: ChatEngineKnowledgeGraphOptions | null; // 知识图谱选项
  llm?: ChatEngineLLMOptions | null;    // 大语言模型选项
  post_verification_url?: string | null; // 后验证URL
  post_verification_token?: string | null; // 后验证Token
  hide_sources?: boolean | null;        // 是否隐藏来源
}

/**
 * 聊天引擎知识库选项接口
 */
export interface ChatEngineKnowledgeBaseOptions {
  /**
   * @deprecated 已弃用
   */
  linked_knowledge_base?: LinkedKnowledgeBaseOptions | null; // 关联的知识库（已弃用）
  linked_knowledge_bases?: { id: number }[] | null; // 关联的知识库列表
}

/**
 * 聊天引擎知识图谱选项接口
 */
export interface ChatEngineKnowledgeGraphOptions {
  depth?: number | null;               // 搜索深度
  enabled?: boolean | null;            // 是否启用
  include_meta?: boolean | null;       // 是否包含元数据
  with_degree?: boolean | null;        // 是否包含度信息
  using_intent_search?: boolean | null; // 是否使用意图搜索
}

/**
 * 聊天引擎大语言模型选项接口
 */
export type ChatEngineLLMOptions = {
  condense_question_prompt?: string | null      // 问题凝练提示词
  text_qa_prompt?: string | null                // 文本问答提示词
  intent_graph_knowledge?: string | null        // 意图图谱知识提示词
  normal_graph_knowledge?: string | null        // 普通图谱知识提示词
  clarifying_question_prompt?: string | null    // 问题澄清提示词
  generate_goal_prompt?: string | null          // 生成目标提示词
  further_questions_prompt?: string | null      // 后续问题提示词
}

/**
 * 关联知识库选项接口
 * @deprecated 已弃用
 */
export interface LinkedKnowledgeBaseOptions {
  id?: number | null;                  // 知识库ID
}

// Zod验证模式定义
const kbOptionsSchema = z.object({
  linked_knowledge_base: z.object({ id: z.number().nullable().optional() }).nullable().optional(),
  linked_knowledge_bases: z.object({ id: z.number() }).array().nullable().optional(),
}).passthrough();

const kgOptionsSchema = z.object({
  depth: z.number().nullable().optional(),
  enabled: z.boolean().nullable().optional(),
  include_meta: z.boolean().nullable().optional(),
  with_degree: z.boolean().nullable().optional(),
  using_intent_search: z.boolean().nullable().optional(),
}).passthrough() satisfies ZodType<ChatEngineKnowledgeGraphOptions>;

const llmOptionsSchema =
  z.object({
    condense_question_prompt: z.string().nullable().optional(),
    text_qa_prompt: z.string().nullable().optional(),
    intent_graph_knowledge: z.string().nullable().optional(),
    normal_graph_knowledge: z.string().nullable().optional(),
    clarifying_question_prompt: z.string().nullable().optional(),
    generate_goal_prompt: z.string().nullable().optional(),
    further_questions_prompt: z.string().nullable().optional(),
    // provider: z.string(),
    // reranker_provider: z.string(),
    // reranker_top_k: z.number(),
  }).passthrough() as ZodType<ChatEngineLLMOptions, any, any>;

const chatEngineOptionsSchema = z.object({
  external_engine_config: z.object({
    stream_chat_api_url: z.string().optional().nullable(),
  }).nullable().optional(),
  clarify_question: z.boolean().nullable().optional(),
  further_questions: z.boolean().nullable().optional(),
  knowledge_base: kbOptionsSchema.nullable().optional(),
  knowledge_graph: kgOptionsSchema.nullable().optional(),
  llm: llmOptionsSchema.nullable().optional(),
  post_verification_url: z.string().nullable().optional(),
  post_verification_token: z.string().nullable().optional(),
  hide_sources: z.boolean().nullable().optional(),
}).passthrough()
  .refine(option => {
    if (!option.knowledge_base?.linked_knowledge_bases?.length) {
      if (option.knowledge_base?.linked_knowledge_base?.id != null) {
        // Frontend temporary migration. Should be removed after backend removed linked_knowledge_base field.
        option.knowledge_base.linked_knowledge_bases = [{
          id: option.knowledge_base.linked_knowledge_base.id,
        }];
        delete option.knowledge_base.linked_knowledge_base;
      }
    }
    return option;
  }) satisfies ZodType<ChatEngineOptions, any, any>;

const chatEngineSchema = z.object({
  id: z.number(),
  name: z.string(),
  updated_at: zodJsonDate(),
  created_at: zodJsonDate(),
  deleted_at: zodJsonDate().nullable(),
  engine_options: chatEngineOptionsSchema,
  llm_id: z.number().nullable(),
  fast_llm_id: z.number().nullable(),
  reranker_id: z.number().nullable(),
  is_default: z.boolean(),
}) satisfies ZodType<ChatEngine, any, any>;

/**
 * 获取默认聊天引擎选项
 * @returns 返回Promise，包含默认的聊天引擎选项
 */
export async function getDefaultChatEngineOptions (): Promise<ChatEngineOptions> {
  return await fetch(requestUrl('/api/v1/admin/chat-engines-default-config'), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(chatEngineOptionsSchema));
}

/**
 * 获取聊天引擎列表
 * @param 分页参数对象，包含page和size
 * @returns 返回Promise，包含分页的聊天引擎列表
 */
export async function listChatEngines ({ page = 1, size = 10 }: PageParams = {}): Promise<Page<ChatEngine>> {
  return await fetch(requestUrl('/api/v1/admin/chat-engines', { page, size }), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(zodPage(chatEngineSchema)));
}

/**
 * 获取指定ID的聊天引擎详情
 * @param id 聊天引擎ID
 * @returns 返回Promise，包含聊天引擎详情信息
 */
export async function getChatEngine (id: number): Promise<ChatEngine> {
  return await fetch(requestUrl(`/api/v1/admin/chat-engines/${id}`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(chatEngineSchema));
}

/**
 * 更新指定ID的聊天引擎
 * @param id 聊天引擎ID
 * @param partial 需要更新的聊天引擎属性
 * @returns 返回Promise
 */
export async function updateChatEngine (id: number, partial: Partial<Pick<ChatEngine, 'name' | 'llm_id' | 'fast_llm_id' | 'reranker_id' | 'engine_options' | 'is_default'>>): Promise<void> {
  await fetch(requestUrl(`/api/v1/admin/chat-engines/${id}`), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
    body: JSON.stringify(partial),
  })
    .then(handleErrors);
}

/**
 * 创建新的聊天引擎
 * @param create 创建聊天引擎所需的参数
 * @returns 返回Promise，包含创建成功的聊天引擎信息
 */
export async function createChatEngine (create: CreateChatEngineParams) {
  return await fetch(requestUrl(`/api/v1/admin/chat-engines`), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
    body: JSON.stringify(create),
  })
    .then(handleResponse(chatEngineSchema));
}

/**
 * 删除指定ID的聊天引擎
 * @param id 聊天引擎ID
 * @returns 返回Promise
 */
export async function deleteChatEngine (id: number): Promise<void> {
  await fetch(requestUrl(`/api/v1/admin/chat-engines/${id}`), {
    method: 'DELETE',
    headers: {
      ...await authenticationHeaders(),
    },
  })
    .then(handleErrors);
}
