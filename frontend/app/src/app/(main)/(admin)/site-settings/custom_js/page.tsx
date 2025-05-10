import { getAllSiteSettings } from '@/api/site-settings';
import { CustomJsSettings } from '@/components/settings/CustomJsSettings';
import { WidgetSnippet } from '@/components/settings/WidgetSnippet';

export default async function CustomJsSettingsPage () {
  const settings = await getAllSiteSettings();

  return (
    <>
      <h2 className="text-xl font-medium mb-4">JS小部件设置</h2>
      <section className="max-w-screen-md space-y-2 mb-8">
        <WidgetSnippet />
        <p className="text-muted-foreground text-xs">复制此HTML片段到您的页面。</p>
      </section>
      <CustomJsSettings schema={settings} />
    </>
  );
}

export const dynamic = 'force-dynamic';
