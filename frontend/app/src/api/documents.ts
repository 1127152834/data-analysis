import { indexStatuses } from '@/api/rag';
import { authenticationHeaders, handleResponse, type Page, type PageParams, requestUrl, zodPage } from '@/lib/request';
import { zodJsonDate } from '@/lib/zod';
import { z, type ZodType } from 'zod';

/**
 * 支持的MIME类型列表
 */
export const mimeTypes = [
  { name: 'Text', value: 'text/plain' },                     // 纯文本
  { name: 'Markdown', value: 'text/markdown' },              // Markdown
  { name: 'Pdf', value: 'application/pdf' },                 // PDF
  { name: 'Microsoft Word (docx)', value: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' },  // Word文档
  { name: 'Microsoft PowerPoint (pptx)', value: 'application/vnd.openxmlformats-officedocument.presentationml.presentation' },  // PowerPoint演示文稿
  { name: 'Microsoft Excel (xlsx)', value: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' },  // Excel表格
] as const satisfies MimeType[];

// 提取所有MIME类型值
const mimeValues: (typeof mimeTypes)[number]['value'] = mimeTypes.map(m => m.value) as never;

/**
 * 文档接口
 */
export interface Document {
  id: number,                      // 文档ID
  name: string,                    // 文档名称
  created_at?: Date | undefined;   // 创建时间
  updated_at?: Date | undefined    // 更新时间
  last_modified_at: Date,          // 最后修改时间
  hash: string                     // 文档哈希值
  content: string                  // 文档内容
  meta: object,                    // 元数据
  mime_type: string,               // MIME类型
  source_uri: string,              // 源文件URI
  index_status: string,            // 索引状态
  index_result?: unknown           // 索引结果
  data_source: {                   // 数据源信息
    id: number                     // 数据源ID
    name: string                   // 数据源名称
  }
  knowledge_base: {                // 知识库信息
    id: number                     // 知识库ID
    name: string                   // 知识库名称
  } | null                         // 可能为空，表示文档未关联知识库
}

/**
 * 文档模式验证
 */
export const documentSchema = z.object({
  id: z.number(),
  name: z.string(),
  created_at: zodJsonDate(),
  updated_at: zodJsonDate(),
  last_modified_at: zodJsonDate(),
  hash: z.string(),
  content: z.string(),
  meta: z.object({}).passthrough(),
  mime_type: z.string(),
  source_uri: z.string(),
  index_status: z.string(),
  index_result: z.unknown(),
  data_source: z.object({
    id: z.number(),
    name: z.string(),
  }),
  knowledge_base: z.object({
    id: z.number(),
    name: z.string(),
  }).nullable(),
}) satisfies ZodType<Document, any, any>;

// 日期格式验证
const zDate = z.coerce.date().or(z.literal('').transform(() => undefined)).optional();
// 日期范围验证
const zDateRange = z.tuple([zDate, zDate]).optional();

/**
 * 文档列表过滤条件模式验证
 */
export const listDocumentsFiltersSchema = z.object({
  search: z.string().optional(),                 // 搜索关键词
  knowledge_base_id: z.number().optional(),      // 知识库ID
  created_at: zDateRange,                        // 创建时间范围
  updated_at: zDateRange,                        // 更新时间范围
  last_modified_at: zDateRange,                  // 最后修改时间范围
  mime_type: z.enum(mimeValues).optional(),      // MIME类型
  index_status: z.enum(indexStatuses).optional(),// 索引状态
});

/**
 * 文档列表过滤条件类型
 */
export type ListDocumentsTableFilters = z.infer<typeof listDocumentsFiltersSchema>;

/**
 * 获取文档列表
 * @param 分页和过滤参数，包含page、size、knowledge_base_id和其他过滤条件
 * @returns 返回Promise，包含分页的文档列表
 */
export async function listDocuments ({ page = 1, size = 10, knowledge_base_id, search, ...filters }: PageParams & ListDocumentsTableFilters = {}): Promise<Page<Document>> {
  const apiFilters = {
    ...filters,
    knowledge_base_id,
    search: search
  };
  const api_url = knowledge_base_id != null ? `/api/v1/admin/knowledge_bases/${knowledge_base_id}/documents` : '/api/v1/admin/documents';
  return await fetch(requestUrl(api_url, { page, size, ...apiFilters }), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(zodPage(documentSchema)));
}

/**
 * 获取单个文档的详细信息
 * @param id 文档ID
 * @returns 返回Promise，包含文档详情
 */
export async function getDocument(id: number): Promise<Document> {
  return await fetch(requestUrl(`/api/v1/admin/documents/${id}`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(documentSchema));
}

/**
 * MIME类型接口
 */
export interface MimeType {
  name: string;   // MIME类型名称
  value: string;  // MIME类型值
}

