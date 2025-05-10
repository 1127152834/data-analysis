'use client';

import { AdminPageHeading } from '@/components/admin-page-heading';
import { SecondaryNavigatorLayout, SecondaryNavigatorLink, SecondaryNavigatorList, SecondaryNavigatorMain } from '@/components/secondary-navigator-list';
import { type ReactNode } from 'react';

export default function SiteSettingsLayout ({ children }: { children: ReactNode }) {
  return (
    <div className="relative">
      <AdminPageHeading
        breadcrumbs={[
          { title: '站点设置' },
        ]}
      />
      <SecondaryNavigatorLayout>
        <SecondaryNavigatorList>
          <SecondaryNavigatorLink pathname="/site-settings">
            网站
          </SecondaryNavigatorLink>
          <SecondaryNavigatorLink pathname="/site-settings/integrations">
            集成
          </SecondaryNavigatorLink>
          <SecondaryNavigatorLink pathname="/site-settings/custom_js">
            JS小部件
          </SecondaryNavigatorLink>
        </SecondaryNavigatorList>
        <SecondaryNavigatorMain className="px-2">
          {children}
        </SecondaryNavigatorMain>
      </SecondaryNavigatorLayout>
    </div>
  );
}
