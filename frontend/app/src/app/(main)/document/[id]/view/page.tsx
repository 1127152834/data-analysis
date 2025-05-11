'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { DateFormat } from '@/components/date-format';
import { ArrowLeftIcon, ChevronRightIcon, FileTextIcon, HomeIcon, LoaderIcon } from 'lucide-react';
import { getDocument } from '@/api/documents';

export default function DocumentViewPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const documentId = parseInt(params.id);
  const [document, setDocument] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDocument() {
      try {
        setLoading(true);
        const doc = await getDocument(documentId);
        setDocument(doc);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch document:', err);
        setError('无法加载文档内容，请稍后再试。');
      } finally {
        setLoading(false);
      }
    }

    fetchDocument();
  }, [documentId]);

  const goBack = () => {
    router.back();
  };

  return (
    <div className="container py-8">
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-4">
        <Button 
          variant="ghost" 
          size="icon" 
          className="h-6 w-6" 
          onClick={goBack}
        >
          <ArrowLeftIcon className="h-4 w-4" />
        </Button>
        <Button 
          variant="ghost" 
          size="icon" 
          className="h-6 w-6"
          onClick={() => router.push('/')}
        >
          <HomeIcon className="h-4 w-4" />
        </Button>
        <ChevronRightIcon className="h-4 w-4" />
        <span>文档详情</span>
      </div>
      
      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-8 w-[250px]" />
          <Skeleton className="h-4 w-[400px]" />
          <Skeleton className="h-[500px] w-full" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-red-500">{error}</div>
          </CardContent>
        </Card>
      ) : document ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileTextIcon className="h-5 w-5" />
                {document.name}
              </CardTitle>
              <CardDescription>
                ID: {document.id}
                {document.source_uri && (
                  <>
                    <br />
                    来源: {document.source_uri}
                  </>
                )}
                <br />
                更新时间: <DateFormat date={document.updated_at} />
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-md">
                <pre className="whitespace-pre-wrap break-words text-sm">
                  {document.content}
                </pre>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6 text-center">
            <div>未找到文档</div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 