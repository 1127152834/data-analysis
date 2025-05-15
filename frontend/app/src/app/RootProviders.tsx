'use client';

import type { PublicWebsiteSettings } from '@/api/site-settings';
import type { BootstrapStatus } from '@/api/system';
import { getMe, type MeInfo } from '@/api/users';
import { AuthProvider } from '@/components/auth/AuthProvider';
import { ChatsProvider } from '@/components/chat/chat-hooks';
import { GtagProvider } from '@/components/gtag-provider';
import { BootstrapStatusProvider } from '@/components/system/BootstrapStatusProvider';
import { Toaster } from '@/components/ui/sonner';
import { SettingProvider } from '@/components/website-setting-provider';
import { type ExperimentalFeatures, ExperimentalFeaturesProvider } from '@/experimental/experimental-features-provider';
import { cn } from '@/lib/utils';
import { ThemeProvider } from 'next-themes';
import type { ReactNode } from 'react';
import useSWR from 'swr';

export interface RootProvidersProps {
  me: MeInfo | undefined;
  children: ReactNode;
  settings: PublicWebsiteSettings;
  bootstrapStatus: BootstrapStatus;
  experimentalFeatures: Partial<ExperimentalFeatures>;
}

// 将Provider分层，减少渲染树级联
const AuthProviderLayer = ({ 
  me, 
  isLoading, 
  isValidating, 
  reload, 
  children 
}: { 
  me: MeInfo | undefined, 
  isLoading: boolean, 
  isValidating: boolean, 
  reload: () => void, 
  children: ReactNode 
}) => (
  <AuthProvider me={me} isLoading={isLoading} isValidating={isValidating} reload={reload}>
    <ChatsProvider>
      {children}
    </ChatsProvider>
  </AuthProvider>
);

export function RootProviders ({ me, settings, bootstrapStatus, experimentalFeatures, children }: RootProvidersProps) {
  const { data, isValidating, isLoading, mutate } = useSWR('api.users.me', getMe, {
    fallbackData: me,
    revalidateOnMount: false,
    revalidateOnFocus: false,
    errorRetryCount: 0,
  });

  return (
    <BootstrapStatusProvider bootstrapStatus={bootstrapStatus}>
      <ThemeProvider
        attribute="class"
        defaultTheme="dark" // 默认深色主题
        enableSystem // 启用系统主题
        disableTransitionOnChange // 禁用主题切换过渡动画
      >
        <SettingProvider
          value={settings}>
          <ExperimentalFeaturesProvider features={experimentalFeatures}>
            <GtagProvider gtagId={settings.ga_id} configured>
              <AuthProviderLayer 
                me={data} 
                isLoading={isLoading} 
                isValidating={isValidating} 
                reload={() => mutate(data, { revalidate: true })}
              >
                {children}
                <Toaster cn={cn} />
              </AuthProviderLayer>
            </GtagProvider>
          </ExperimentalFeaturesProvider>
        </SettingProvider>
      </ThemeProvider>
    </BootstrapStatusProvider>
  );
}
