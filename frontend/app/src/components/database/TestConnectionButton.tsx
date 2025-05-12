'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ConnectionTestResponse } from '@/api/database';
import { Loader2 } from 'lucide-react';

interface TestConnectionButtonProps {
  onTest: () => Promise<ConnectionTestResponse>;
  disabled?: boolean;
  hideResult?: boolean;
}

export function TestConnectionButton({ onTest, disabled, hideResult = false }: TestConnectionButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<ConnectionTestResponse | null>(null);

  const handleTest = async () => {
    setIsLoading(true);
    setResult(null);
    
    try {
      const testResult = await onTest();
      if (!hideResult) {
        setResult(testResult);
      }
    } catch (error) {
      if (!hideResult) {
        setResult({
          success: false,
          message: error instanceof Error ? error.message : '测试连接失败',
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <Button
        type="button"
        variant="outline"
        onClick={handleTest}
        disabled={disabled || isLoading}
        className="w-full"
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            测试中...
          </>
        ) : (
          '测试连接'
        )}
      </Button>
      
      {!hideResult && result && (
        <div className={`mt-2 text-sm ${result.success ? 'text-green-600' : 'text-red-600'}`}>
          {result.message}
        </div>
      )}
    </div>
  );
} 