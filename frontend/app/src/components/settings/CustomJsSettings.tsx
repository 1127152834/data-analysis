'use client';

import type { AllSettings } from '@/api/site-settings';
import { SettingsField } from '@/components/settings/SettingsField';
import { StringArrayField } from '@/components/settings/StringArrayField';
import { z } from 'zod';

// 字段名称翻译映射
const fieldNameMap = {
  custom_js_logo_src: '自定义JS Logo源',
  custom_js_button_label: '自定义JS按钮标签',
  custom_js_button_img_src: '自定义JS按钮图片源',
  custom_js_example_questions: '自定义JS示例问题'
};

export function CustomJsSettings ({ schema }: { schema: AllSettings }) {
  return (
    <div className="space-y-8 max-w-screen-md">
      <section className="space-y-6">
        <SettingsField 
          name="custom_js_logo_src" 
          item={schema.custom_js_logo_src} 
          displayName={fieldNameMap.custom_js_logo_src} 
        />
        <SettingsField 
          name="custom_js_button_label" 
          item={schema.custom_js_button_label} 
          displayName={fieldNameMap.custom_js_button_label} 
        />
        <SettingsField 
          name="custom_js_button_img_src" 
          item={schema.custom_js_button_img_src} 
          displayName={fieldNameMap.custom_js_button_img_src} 
        />
        <SettingsField 
          name="custom_js_example_questions" 
          item={schema.custom_js_example_questions} 
          arrayItemSchema={z.string()} 
          displayName={fieldNameMap.custom_js_example_questions}
        >
          {props => <StringArrayField {...props} />}
        </SettingsField>
      </section>
    </div>
  );
}