'use client';

import type { AllSettings } from '@/api/site-settings';
import { SettingsField } from '@/components/settings/SettingsField';

// 字段名称翻译映射
const fieldNameMap = {
  langfuse_public_key: 'Langfuse公钥',
  langfuse_secret_key: 'Langfuse密钥',
  langfuse_host: 'Langfuse主机地址',
  enable_post_verifications: '启用全局发布验证',
  enable_post_verifications_for_widgets: '启用组件发布验证'
};

export function IntegrationsSettings ({ schema, showPostVerificationSettings }: { schema: AllSettings, showPostVerificationSettings: boolean }) {
  return (
    <div className="space-y-8 max-w-screen-md">
      <h2 className="text-xl font-medium mb-4">集成设置</h2>
      <LangfuseSettings schema={schema} />
      {showPostVerificationSettings && <ExperimentalPostVerificationSettings schema={schema} />}
    </div>
  );
}

export function LangfuseSettings ({ schema, hideTitle, disabled, onChanged }: { schema: AllSettings, hideTitle?: boolean, disabled?: boolean, onChanged?: () => void }) {
  return (
    <section className="space-y-6">
      {!hideTitle && <h2 className="text-lg font-medium">Langfuse 集成</h2>}
      <SettingsField 
        name="langfuse_public_key" 
        item={schema.langfuse_public_key} 
        onChanged={onChanged} 
        disabled={disabled}
        displayName={fieldNameMap.langfuse_public_key}
      />
      <SettingsField 
        name="langfuse_secret_key" 
        item={schema.langfuse_secret_key} 
        onChanged={onChanged} 
        disabled={disabled}
        displayName={fieldNameMap.langfuse_secret_key}
      />
      <SettingsField 
        name="langfuse_host" 
        item={schema.langfuse_host} 
        onChanged={onChanged} 
        disabled={disabled}
        displayName={fieldNameMap.langfuse_host}
      />
    </section>
  );
}

export function ExperimentalPostVerificationSettings ({ schema, hideTitle, disabled, onChanged }: { schema: AllSettings, hideTitle?: boolean, disabled?: boolean, onChanged?: () => void }) {
  return (
    <section className="space-y-6">
      {!hideTitle && <h2 className="text-lg font-medium">[实验性功能] 发布验证</h2>}
      <SettingsField 
        name="enable_post_verifications" 
        item={schema.enable_post_verifications} 
        onChanged={onChanged} 
        disabled={disabled}
        displayName={fieldNameMap.enable_post_verifications}
      />
      <SettingsField 
        name="enable_post_verifications_for_widgets" 
        item={schema.enable_post_verifications_for_widgets} 
        onChanged={onChanged} 
        disabled={disabled}
        displayName={fieldNameMap.enable_post_verifications_for_widgets}
      />
    </section>
  );
}
