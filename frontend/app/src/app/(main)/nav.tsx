'use client';

import type { PublicWebsiteSettings } from '@/api/site-settings';
import { Branding } from '@/components/branding';
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader } from '@/components/ui/sidebar';
import { NavContent } from './nav-content';
import { NavFooter } from './nav-footer';

export function SiteSidebar({ setting }: { setting: PublicWebsiteSettings }) {
  return (
    <Sidebar>
      <SidebarHeader>
        <Branding setting={setting} />
      </SidebarHeader>
      <SidebarContent>
        <NavContent />
      </SidebarContent>
      <SidebarFooter>
        <NavFooter />
      </SidebarFooter>
    </Sidebar>
  );
}