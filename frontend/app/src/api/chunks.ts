import { z } from 'zod';
import { authenticationHeaders, handleResponse, requestUrl } from '@/lib/request';

/**
 * 文本块数据模型
 */
export const chunkSchema = z.object({
  id: z.number(),
  hash: z.string(),
  text: z.string(),
  embedding: z.array(z.number()).nullable(),
  meta: z.record(z.unknown()),
  document_id: z.number(),
  source_uri: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type Chunk = z.infer<typeof chunkSchema>;

/**
 * 根据ID获取文本块内容
 * @param id 文本块ID
 * @returns 返回Promise，包含文本块详情
 */
export async function getChunk(id: string | number) {
  return await fetch(requestUrl(`/api/v1/chunks/${id}`), {
    headers: await authenticationHeaders(),
  })
    .then(handleResponse(chunkSchema));
}


/**
 * 根据ID获取文本块内容
 * @param id 文本块ID
 * @returns 返回Promise，包含文本块详情
 */
export const getChunkById = async (
  chunkId: string
): Promise<{ id: string; text: string } | null> => {
  try {
    console.log(`请求chunk ID: ${chunkId}`);
    const response = await fetch(
      requestUrl(`/api/v1/chunks/id/${chunkId}`)
    );

    if (!response.ok) {
      console.error(`获取chunk内容失败，状态码: ${response.status}`);
      return null;
    }

    const data = await response.json();
    return {
      id: chunkId,
      text: data.content || data.text || "",
    };
  } catch (error) {
    console.error(`获取chunk内容异常: ${error instanceof Error ? error.message : String(error)}`);
    return null;
  }
};

