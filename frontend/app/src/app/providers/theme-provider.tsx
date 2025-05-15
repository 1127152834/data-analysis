'use client';

import { ThemeProvider as NextThemeProvider } from 'next-themes';
import { ReactNode } from 'react';

export function ThemeProviderWrapper({ children }: { children: ReactNode }) {
  return (
    <NextThemeProvider
      attribute="class"
      defaultTheme="dark" // 默认深色主题
      enableSystem // 启用系统主题
      disableTransitionOnChange // 禁用主题切换过渡动画
    >
      {children}
    </NextThemeProvider>
  );
} 