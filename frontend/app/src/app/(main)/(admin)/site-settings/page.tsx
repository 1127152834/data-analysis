import { getAllSiteSettings } from '@/api/site-settings';
import { WebsiteSettings } from '@/components/settings/WebsiteSettings';

export default async function SiteSettingsPage () {
  const settings = await getAllSiteSettings();

  return (
    <>
      <h2 className="text-xl font-medium mb-4">网站基本设置</h2>
      <WebsiteSettings schema={settings} />
    </>
  );
}

export const dynamic = 'force-dynamic';
