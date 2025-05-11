import { Button } from '@/components/ui/button';
import { Loader2, Database, CheckCircle } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

// 测试连接按钮组件
interface TestConnectionButtonProps {
  onClick: () => void;
  loading?: boolean;
  success?: boolean;
}

export function TestConnectionButton({ onClick, loading, success }: TestConnectionButtonProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button 
            type="button" 
            variant={success ? "outline" : "secondary"}
            onClick={onClick} 
            disabled={loading}
            className={`gap-2 ${success ? 'border-green-500 text-green-600 hover:bg-green-50' : ''}`}
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>测试中...</span>
              </>
            ) : success ? (
              <>
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>连接成功</span>
              </>
            ) : (
              <>
                <Database className="h-4 w-4" />
                <span>测试连接</span>
              </>
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p>测试数据库连接是否可用</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
} 