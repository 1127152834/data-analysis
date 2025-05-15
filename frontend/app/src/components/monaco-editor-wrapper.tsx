'use client';

import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';

// 动态导入Monaco编辑器
const DynamicMonacoEditor = dynamic(
  () => import('@/components/monaco-editor'),
  {
    ssr: false,
    loading: () => <Skeleton className="h-[400px] w-full" />,
  }
);

export default DynamicMonacoEditor; 