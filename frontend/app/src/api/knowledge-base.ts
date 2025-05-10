import { type BaseCreateDatasourceParams, type CreateDatasourceSpecParams, type Datasource, type DatasourceKgIndexError, datasourceSchema, type DatasourceVectorIndexError } from '@/api/datasources';
import { documentSchema } from '@/api/documents';
import { type EmbeddingModelSummary, embeddingModelSummarySchema } from '@/api/embedding-models';
import { type LLMSummary, llmSummarySchema } from '@/api/llms';
import { type IndexProgress, indexSchema, indexStatusSchema, type IndexTotalStats, totalSchema } from '@/api/rag';
import { authenticationHeaders, handleErrors, handleResponse, type PageParams, requestUrl, zodPage } from '@/lib/request';
import { zodJsonDate } from '@/lib/zod';
import { z, type ZodType } from 'zod';

/**
 * 知识库索引方法类型
 * vector: 向量索引
 * knowledge_graph: 知识图谱
 */
export type KnowledgeBaseIndexMethod = 'vector' | 'knowledge_graph';

/**
 * 创建知识库所需参数接口
 */
export interface CreateKnowledgeBaseParams {
  name: string;                         // 知识库名称
  description?: string | null;          // 知识库描述
  index_methods: KnowledgeBaseIndexMethod[]; // 索引方法
  llm_id?: number | null;               // 大语言模型ID
  embedding_model_id?: number | null;   // 嵌入模型ID
  data_sources: (BaseCreateDatasourceParams & CreateDatasourceSpecParams)[]; // 数据源
}

/**
 * 更新知识库所需参数接口
 */
export interface UpdateKnowledgeBaseParams {
  name?: string;                        // 知识库名称
  description?: string | null;          // 知识库描述
}

/**
 * 知识库摘要信息接口
 */
export interface KnowledgeBaseSummary {
  id: number;                           // 知识库ID
  name: string;                         // 知识库名称
  description: string | null;           // 知识库描述
  index_methods: KnowledgeBaseIndexMethod[]; // 索引方法
  documents_total?: number;             // 文档总数
  data_sources_total?: number;          // 数据源总数
  created_at: Date;                     // 创建时间
  updated_at: Date;                     // 更新时间
  creator: {                            // 创建者
    id: string;
  };
}

/**
 * 知识库完整信息接口，继承自KnowledgeBaseSummary
 */
export interface KnowledgeBase extends KnowledgeBaseSummary {
  data_sources: Datasource[];           // 数据源列表
  llm?: LLMSummary | null;              // 大语言模型信息
  embedding_model?: EmbeddingModelSummary | null; // 嵌入模型信息
  chunking_config: KnowledgeBaseChunkingConfig | null; // 分块配置
}

/**
 * 知识图谱索引进度接口
 */
export type KnowledgeGraphIndexProgress = {
  vector_index: IndexProgress          // 向量索引进度
  documents: IndexTotalStats           // 文档统计
  chunks: IndexTotalStats              // 文本块统计
  kg_index?: IndexProgress             // 知识图谱索引进度
  entities?: IndexTotalStats           // 实体统计
  relationships?: IndexTotalStats      // 关系统计
}

/**
 * 知识库分块器类型
 */
export type KnowledgeBaseSplitterType = KnowledgeBaseChunkingSplitterRule['splitter'];

/**
 * 知识库分块器-句子分块配置
 */
export type KnowledgeBaseChunkingSentenceSplitterConfig = {
  chunk_size: number                   // 分块大小
  chunk_overlap: number                // 分块重叠大小
  paragraph_separator: string          // 段落分隔符
}

/**
 * 知识库分块器-Markdown分块配置
 */
export type KnowledgeBaseChunkingMarkdownSplitterConfig = {
  chunk_size: number                   // 分块大小
  chunk_header_level: number           // 标题级别
}

/**
 * 知识库分块器-句子分块规则
 */
export type KnowledgeBaseChunkingSentenceSplitterRule = {
  splitter: 'SentenceSplitter'         // 句子分块器
  splitter_config: KnowledgeBaseChunkingSentenceSplitterConfig // 句子分块配置
}

/**
 * 知识库分块器-Markdown分块规则
 */
export type KnowledgeBaseChunkingMarkdownSplitterRule = {
  splitter: 'MarkdownSplitter'         // Markdown分块器
  splitter_config: KnowledgeBaseChunkingMarkdownSplitterConfig // Markdown分块配置
}

/**
 * 知识库分块器规则联合类型
 */
export type KnowledgeBaseChunkingSplitterRule = KnowledgeBaseChunkingSentenceSplitterRule | KnowledgeBaseChunkingMarkdownSplitterRule;

/**
 * 知识库分块配置-通用模式
 */
export type KnowledgeBaseChunkingConfigGeneral = {
  mode: 'general'                      // 通用模式
} & KnowledgeBaseChunkingSentenceSplitterConfig;

/**
 * 知识库分块配置-高级模式
 */
export type KnowledgeBaseChunkingConfigAdvanced = {
  mode: 'advanced'                     // 高级模式
  rules: {                            // 不同文件类型的分块规则
    'text/plain': KnowledgeBaseChunkingSplitterRule;
    'text/markdown': KnowledgeBaseChunkingSplitterRule
  }
}

/**
 * 知识库分块配置联合类型
 */
export type KnowledgeBaseChunkingConfig = KnowledgeBaseChunkingConfigGeneral | KnowledgeBaseChunkingConfigAdvanced;

/**
 * 知识图谱文档块类型
 */
export type KnowledgeGraphDocumentChunk = z.infer<typeof knowledgeGraphDocumentChunkSchema>;

// Zod验证模式定义
const knowledgeBaseChunkingSentenceSplitterConfigSchema = z.object({
  chunk_size: z.number().int().min(1),
  chunk_overlap: z.number().int().min(0),
  paragraph_separator: z.string(),
}) satisfies z.ZodType<KnowledgeBaseChunkingSentenceSplitterConfig, any, any>;

const knowledgeBaseChunkingMarkdownSplitterConfigSchema = z.object({
  chunk_size: z.number().int().min(1),
  chunk_header_level: z.number().int().min(1).max(6),
}) satisfies z.ZodType<KnowledgeBaseChunkingMarkdownSplitterConfig, any, any>;

const knowledgeBaseChunkingSplitterRuleSchema = z.discriminatedUnion('splitter', [
  z.object({
    splitter: z.literal('MarkdownSplitter'),
    splitter_config: knowledgeBaseChunkingMarkdownSplitterConfigSchema,
  }),
  z.object({
    splitter: z.literal('SentenceSplitter'),
    splitter_config: knowledgeBaseChunkingSentenceSplitterConfigSchema,
  }),
]) satisfies z.ZodType<KnowledgeBaseChunkingSplitterRule, any, any>;

export const knowledgeBaseChunkingConfigSchema = z.discriminatedUnion('mode', [
  z.object({
    mode: z.literal('general'),
    chunk_size: z.number().int().min(1),
    chunk_overlap: z.number().int().min(0),
    paragraph_separator: z.string(),
  }),
  z.object({
    mode: z.literal('advanced'),
    rules: z.object({
      'text/plain': knowledgeBaseChunkingSplitterRuleSchema,
      'text/markdown': knowledgeBaseChunkingSplitterRuleSchema,
    }),
  }),
]) satisfies z.ZodType<KnowledgeBaseChunkingConfig, any, any>;

const knowledgeBaseSummarySchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string().nullable(),
  index_methods: z.enum(['vector', 'knowledge_graph']).array(),
  documents_total: z.number().optional(),
  data_sources_total: z.number().optional(),
  created_at: zodJsonDate(),
  updated_at: zodJsonDate(),
  creator: z.object({
    id: z.string(),
  }),
}) satisfies ZodType<KnowledgeBaseSummary, any, any>;

const knowledgeBaseSchema = knowledgeBaseSummarySchema.extend({
  data_sources: datasourceSchema.array(),
  llm: llmSummarySchema.nullable().optional(),
  embedding_model: embeddingModelSummarySchema.nullable().optional(),
  chunking_config: knowledgeBaseChunkingConfigSchema.nullable(),
}) satisfies ZodType<KnowledgeBase, any, any>;

const knowledgeGraphIndexProgressSchema = z.object({
  vector_index: indexSchema,
  documents: totalSchema,
  chunks: totalSchema,
  kg_index: indexSchema.optional(),
  entities: totalSchema.optional(),
  relationships: totalSchema.optional(),
}) satisfies ZodType<KnowledgeGraphIndexProgress>;

const knowledgeGraphDocumentChunkSchema = z.object({
  id: z.string(),
  document_id: z.number(),
  hash: z.string(),
  text: z.string(),
  meta: z.object({}).passthrough(),
  embedding: z.number().array(),
  relations: z.any(),
  source_uri: z.string(),
  index_status: indexStatusSchema,
  index_result: z.string().nullable(),
  created_at: zodJsonDate(),
  updated_at: zodJsonDate(),
});

const vectorIndexErrorSchema = z.object({
  document_id: z.number(),
  document_name: z.string(),
  source_uri: z.string(),
  error: z.string().nullable(),
}) satisfies ZodType<DatasourceVectorIndexError, any, any>;

const kgIndexErrorSchema = z.object({
  document_id: z.number(),
  document_name: z.string(),
  chunk_id: z.string(),
  source_uri: z.string(),
  error: z.string().nullable(),
}) satisfies ZodType<DatasourceKgIndexError, any, any>;

const knowledgeBaseLinkedChatEngine = z.object({
  id: z.number(),
  name: z.string(),
  is_default: z.boolean(),
});

/**
 * 获取知识库列表
 * @param 分页参数对象，包含page和size
 * @returns 返回Promise，包含分页的知识库列表
 */
export async function listKnowledgeBases ({ page = 1, size = 10 }: PageParams) {
  return await fetch(requestUrl('/api/v1/admin/knowledge_bases', { page, size }), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(zodPage(knowledgeBaseSummarySchema)));
}

/**
 * 获取指定ID的知识库详情
 * @param id 知识库ID
 * @returns 返回Promise，包含知识库详情信息
 */
export async function getKnowledgeBaseById (id: number): Promise<KnowledgeBase> {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(knowledgeBaseSchema));
}

/**
 * 获取知识库中指定文档的文本块
 * @param id 知识库ID 
 * @param documentId 文档ID
 * @returns 返回Promise，包含文档文本块数组
 */
export async function getKnowledgeBaseDocumentChunks (id: number, documentId: number) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/documents/${documentId}/chunks`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(knowledgeGraphDocumentChunkSchema.array()));
}

/**
 * 获取知识库中指定文档的详情
 * @param id 知识库ID
 * @param documentId 文档ID
 * @returns 返回Promise，包含文档详情信息
 */
export async function getKnowledgeBaseDocument (id: number, documentId: number) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/documents/${documentId}`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(documentSchema.omit({ knowledge_base: true, data_source: true })));
}

/**
 * 获取知识库关联的聊天引擎列表
 * @param id 知识库ID
 * @returns 返回Promise，包含关联的聊天引擎数组
 */
export async function getKnowledgeBaseLinkedChatEngines (id: number) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/linked_chat_engines`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(knowledgeBaseLinkedChatEngine.array()));
}

/**
 * 删除知识库中的指定文档
 * @param id 知识库ID
 * @param documentId 文档ID
 * @returns 返回Promise
 */
export async function deleteKnowledgeBaseDocument (id: number, documentId: number) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/documents/${documentId}`), {
    method: 'DELETE',
    headers: await authenticationHeaders(),
  })
    .then(handleErrors);
}

/**
 * 重建知识库文档索引
 * @param kb_id 知识库ID
 * @param doc_id 文档ID
 * @returns 返回Promise
 */
export async function rebuildKBDocumentIndex (kb_id: number, doc_id: number) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${kb_id}/documents/${doc_id}/reindex`), {
    method: 'POST',
    headers: await authenticationHeaders(),
  })
    .then(handleErrors);
}

/**
 * 创建新的知识库
 * @param params 创建知识库所需的参数
 * @returns 返回Promise，包含创建成功的知识库信息
 */
export async function createKnowledgeBase (params: CreateKnowledgeBaseParams) {
  return await fetch(requestUrl('/api/v1/admin/knowledge_bases'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
    body: JSON.stringify(params),
  }).then(handleResponse(knowledgeBaseSchema));
}

/**
 * 更新指定ID的知识库信息
 * @param id 知识库ID
 * @param params 更新知识库所需的参数
 * @returns 返回Promise，包含更新后的知识库信息
 */
export async function updateKnowledgeBase (id: number, params: UpdateKnowledgeBaseParams) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}`), {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...await authenticationHeaders(),
    },
    body: JSON.stringify(params),
  }).then(handleResponse(knowledgeBaseSchema));
}

/**
 * 获取知识图谱索引的进度信息
 * @param id 知识库ID
 * @returns 返回Promise，包含知识图谱索引进度信息
 */
export async function getKnowledgeGraphIndexProgress (id: number): Promise<KnowledgeGraphIndexProgress> {
  return fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/overview`), {
    headers: await authenticationHeaders(),
  }).then(handleResponse(knowledgeGraphIndexProgressSchema));
}

/**
 * 获取知识库向量索引的错误列表
 * @param id 知识库ID
 * @param 分页参数对象，包含page和size
 * @returns 返回Promise，包含分页的向量索引错误列表
 */
export async function listKnowledgeBaseVectorIndexErrors (id: number, { page = 1, size = 10 }: PageParams = {}) {
  return fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/vector-index-errors`, { page, size }), {
    headers: await authenticationHeaders(),
  }).then(handleResponse(zodPage(vectorIndexErrorSchema)));
}

/**
 * 获取知识库知识图谱索引的错误列表
 * @param id 知识库ID
 * @param 分页参数对象，包含page和size
 * @returns 返回Promise，包含分页的知识图谱索引错误列表
 */
export async function listKnowledgeBaseKgIndexErrors (id: number, { page = 1, size = 10 }: PageParams = {}) {
  return fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/kg-index-errors`, { page, size }), {
    headers: await authenticationHeaders(),
  }).then(handleResponse(zodPage(kgIndexErrorSchema)));
}

/**
 * 重试知识库中所有失败的索引任务
 * @param id 知识库ID
 * @returns 返回Promise
 */
export async function retryKnowledgeBaseAllFailedTasks (id: number) {
  return fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}/retry-failed-index-tasks`), {
    method: 'POST',
    headers: {
      ...await authenticationHeaders(),
      'Content-Type': 'application/json',
    },
  }).then(handleErrors);
}

/**
 * 删除指定ID的知识库
 * @param id 知识库ID
 * @returns 返回Promise
 */
export async function deleteKnowledgeBase (id: number) {
  return await fetch(requestUrl(`/api/v1/admin/knowledge_bases/${id}`), {
    method: 'DELETE',
    headers: await authenticationHeaders(),
  })
    .then(handleErrors);
}
