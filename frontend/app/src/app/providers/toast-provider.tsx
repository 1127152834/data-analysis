'use client';

import { Toaster } from '@/components/ui/toaster';
import { ReactNode } from 'react';

export function ToastProviderWrapper({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <Toaster />
    </>
  );
} 