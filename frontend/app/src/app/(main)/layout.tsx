import { getPublicSiteSettings } from '@/api/site-settings';
import { MainLayoutClient } from './layout-client';
import { ReactNode } from 'react';
import { cache } from 'react';

// 缓存站点设置查询以提高性能
const cachedGetSettings = cache(getPublicSiteSettings);

export default async function Layout({ children }: {
  children: ReactNode
}) {
  // 在服务器端获取设置
  const setting = await cachedGetSettings();
  
  // 使用客户端组件包装内容
  return (
    <MainLayoutClient setting={setting}>
      {children}
    </MainLayoutClient>
  );
}
