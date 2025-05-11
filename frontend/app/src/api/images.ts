import { authenticationHeaders, handleResponse, requestUrl } from '@/lib/request';
import { z } from 'zod';

/**
 * 图片上传响应结构定义
 */
export const imageUploadSchema = z.object({
  name: z.string(),
  size: z.number(),
  path: z.string(),
  url: z.string(),
  mime_type: z.string()
});

export type ImageUploadResult = z.infer<typeof imageUploadSchema>;

/**
 * 上传图片到服务器
 * 
 * @param files 要上传的图片文件数组
 * @returns 上传结果
 */
export async function uploadImages(files: File[]): Promise<ImageUploadResult[]> {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  return fetch(requestUrl(`/api/v1/admin/images/upload`), {
    method: 'POST',
    headers: {
      ...await authenticationHeaders(),
    },
    body: formData,
  }).then(handleResponse(imageUploadSchema.array()));
} 