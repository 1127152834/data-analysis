import { useId, useState } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { uploadImages } from '@/api/images';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';

export interface ImageUploadInputProps {
  name?: string;
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  ref?: React.Ref<HTMLButtonElement>;
  onBlur?: () => void;
}

/**
 * 图片上传控件
 * 
 * 支持上传图片到服务器，并返回图片URL
 */
export const ImageUploadInput = ({
  name,
  value,
  onChange,
  disabled,
  ref,
  onBlur,
  ...props
}: ImageUploadInputProps) => {
  const id = useId();
  const [isUploading, setIsUploading] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | undefined>(value);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.item(0);
    if (!file) return;

    try {
      setIsUploading(true);
      // 创建本地预览URL
      const localPreviewUrl = URL.createObjectURL(file);
      setPreviewUrl(localPreviewUrl);

      // 上传图片到服务器
      const results = await uploadImages([file]);
      
      if (results && results.length > 0) {
        const imageUrl = results[0].url;
        onChange?.(imageUrl);
        toast.success('图片上传成功');
      } else {
        setPreviewUrl(value); // 恢复原有预览
        toast.error('图片上传失败');
      }
    } catch (error) {
      console.error('上传图片出错:', error);
      setPreviewUrl(value); // 恢复原有预览
      toast.error('图片上传失败: ' + (error instanceof Error ? error.message : String(error)));
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        {previewUrl && (
          <div className="w-full h-60 min-h-[200px] relative mb-2 border rounded-md overflow-hidden">
            <img 
              src={previewUrl} 
              alt="预览图片" 
              className="w-full h-full object-contain" 
              onError={() => setPreviewUrl(undefined)}
            />
          </div>
        )}
        <input
          className="hidden"
          id={id}
          name={name}
          type="file"
          accept="image/jpeg,image/png,image/gif,image/svg+xml,image/webp"
          onChange={handleFileChange}
          disabled={disabled || isUploading}
        />
        <Button
          variant="outline"
          disabled={disabled || isUploading}
          ref={ref}
          onBlur={onBlur}
          {...props}
          className={cn(
            'flex w-full justify-center font-normal',
            (value == null && !previewUrl) && 'text-muted-foreground',
            isUploading && 'opacity-70 cursor-not-allowed'
          )}
          onClick={(event) => {
            (props as any).onClick?.(event);
            if (!event.defaultPrevented && !isUploading) {
              document.getElementById(id)?.click();
            }
          }}
          type="button"
        >
          {isUploading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {isUploading ? '上传中...' : (previewUrl ? '更换图片' : '选择图片')}
        </Button>
      </div>

      {previewUrl && (
        <div className="text-xs text-muted-foreground truncate">
          {value || '本地预览'}
        </div>
      )}
    </div>
  );
}; 