import { type KnowledgeBase, type KnowledgeBaseChunkingConfig, type KnowledgeBaseChunkingConfigAdvanced, type KnowledgeBaseChunkingConfigGeneral, knowledgeBaseChunkingConfigSchema, type KnowledgeBaseChunkingMarkdownSplitterConfig, type KnowledgeBaseChunkingSentenceSplitterConfig, type KnowledgeBaseChunkingSplitterRule } from '@/api/knowledge-base';
import { FormInput } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { createAccessorHelper, GeneralSettingsField } from '@/components/settings-form';
import { FormField, FormItem, FormLabel } from '@/components/ui/form.beta';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { cn } from '@/lib/utils';
import { cloneElement, type ReactElement } from 'react';

const helper = createAccessorHelper<KnowledgeBase>();

export function KnowledgeBaseChunkingConfigFields () {
  return (
    <GeneralSettingsField
      accessor={helper.field('chunking_config', defaultConfig)}
      schema={knowledgeBaseChunkingConfigSchema}
    >
      <ModeSwitch />
    </GeneralSettingsField>
  );
}

const fieldLayout = formFieldLayout<{ value: KnowledgeBaseChunkingConfigGeneral }>();
const advancedFieldLayout = formFieldLayout<{ value: KnowledgeBaseChunkingConfigAdvanced }>();

function ModeSwitch () {
  return (
    <FormField<{ value: KnowledgeBase['chunking_config'] }, 'value'>
      name="value"
      render={(field, form) => <>
        <FormItem>
          <FormLabel>
            分块模式
          </FormLabel>
          <ToggleGroup
            className="w-full flex items-center"
            type="single"
            value={field.state.value?.mode ?? undefined}
            onValueChange={(value => {
              field.setValue(switchMode(value as never));
            })}
            onBlur={field.handleBlur}
          >
            <ToggleGroupItem className="flex-1 border block text-left font-normal h-auto py-4 opacity-50 data-[state=on]:opacity-100 hover:opacity-100 hover:bg-transparent hover:text-foreground transition-all" value="general">
              <div className="font-semibold">
                通用
              </div>
              <p className="text-muted-foreground text-xs">使用最佳实践处理不同类型的文档</p>
            </ToggleGroupItem>
            <ToggleGroupItem className="flex-1 border block text-left font-normal h-auto py-4 opacity-50 data-[state=on]:opacity-100 hover:opacity-100 hover:bg-transparent hover:text-foreground transition-all" value="advanced">
              <div className="font-semibold">
                高级
              </div>
              <p className="text-muted-foreground text-xs">通过规则自定义不同文件类型的处理过程</p>
            </ToggleGroupItem>
          </ToggleGroup>
          <div className="pl-4 border-l-4">
            {form.state.values.value?.mode === 'general' && <GeneralChunkingConfig />}
            {form.state.values.value?.mode === 'advanced' && <AdvancedChunkingConfig />}
          </div>
        </FormItem>
      </>}
    />
  );
}

function GeneralChunkingConfig () {
  return (
    <div className="grid md:grid-cols-3 gap-4">
      <fieldLayout.Basic name="value.chunk_size" label="分块大小">
        <FormInputLayout suffix="tokens">
          <FormInput type="number" />
        </FormInputLayout>
      </fieldLayout.Basic>
      <fieldLayout.Basic name="value.chunk_overlap" label="分块重叠">
        <FormInputLayout suffix="tokens">
          <FormInput type="number" />
        </FormInputLayout>
      </fieldLayout.Basic>
      <fieldLayout.Basic name="value.paragraph_separator" label="段落分隔符">
        <FormInput />
      </fieldLayout.Basic>
    </div>
  );
}

function AdvancedChunkingConfig () {
  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <div className="text-sm font-medium text-muted-foreground">纯文本 (text/plain)</div>
        <SplitterRuleConfig rule={"text/plain" as const} />
      </div>
      <div className="space-y-2">
        <div className="text-sm font-medium text-muted-foreground">Markdown (text/markdown)</div>
        <SplitterRuleConfig rule={"text/markdown" as const} />
      </div>
    </div>
  );
}

function SplitterRuleConfig ({ rule }: { rule: "text/plain" | "text/markdown" }) {
  const name = `value.rules.${rule}` as const;
  return (
    <div className="space-y-4">
      <FormField<{ value: KnowledgeBaseChunkingConfigAdvanced }, typeof name>
        name={name}
        render={(field, form) => {
          // 添加默认值以解决可能的 undefined 问题
          const defaultValue = rule === 'text/markdown' 
            ? {
                splitter: 'MarkdownSplitter' as const,
                splitter_config: switchSplitter('MarkdownSplitter')
              }
            : {
                splitter: 'SentenceSplitter' as const,
                splitter_config: switchSplitter('SentenceSplitter')
              };
          
          const currentValue = field.state.value || defaultValue;
          
          return (
          <>
            <Select
              name={name}
              value={currentValue.splitter}
              onValueChange={value => {
                const newSplitter = value as 'SentenceSplitter' | 'MarkdownSplitter';
                // @ts-ignore - 类型系统限制问题
                field.setValue({
                  splitter: newSplitter,
                  splitter_config: newSplitter === 'SentenceSplitter' 
                    ? switchSplitter('SentenceSplitter') 
                    : switchSplitter('MarkdownSplitter'),
                });
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="SentenceSplitter">SentenceSplitter</SelectItem>
                <SelectItem value="MarkdownSplitter">MarkdownSplitter</SelectItem>
              </SelectContent>
            </Select>

            {currentValue.splitter === 'SentenceSplitter' && (
              <div className="pl-4 grid grid-cols-3 gap-4">
                <advancedFieldLayout.Basic name={`value.rules.${rule}.splitter_config.chunk_size` as any} label="分块大小">
                  <FormInputLayout suffix="tokens">
                    <FormInput type="number" min={1} step={1} />
                  </FormInputLayout>
                </advancedFieldLayout.Basic>
                <advancedFieldLayout.Basic name={`value.rules.${rule}.splitter_config.chunk_overlap` as any} label="分块重叠">
                  <FormInputLayout suffix="tokens">
                    <FormInput type="number" min={0} step={1} />
                  </FormInputLayout>
                </advancedFieldLayout.Basic>
                <advancedFieldLayout.Basic name={`value.rules.${rule}.splitter_config.paragraph_separator` as any} label="段落分隔符">
                  <FormInput />
                </advancedFieldLayout.Basic>
              </div>
            )}
            {currentValue.splitter === 'MarkdownSplitter' && (
              <div className="pl-4 grid grid-cols-3 gap-4">
                <advancedFieldLayout.Basic name={`value.rules.${rule}.splitter_config.chunk_size` as any} label="分块大小">
                  <FormInputLayout suffix="tokens">
                    <FormInput type="number" min={1} step={1} />
                  </FormInputLayout>
                </advancedFieldLayout.Basic>
                <advancedFieldLayout.Basic name={`value.rules.${rule}.splitter_config.chunk_header_level` as any} label="分块标题级别">
                  <FormInput type="number" min={1} max={6} step={1} />
                </advancedFieldLayout.Basic>
              </div>
            )}
          </>
          );
        }}
      />
    </div>
  );
}

function FormInputLayout ({ suffix, children, ...props }: { suffix: string, children: ReactElement }) {
  return (
    <div className="relative">
      {cloneElement(children, {
        className: cn((props as any).className, 'pr-14'),
        ...props,
      } as any)}
      <span className="absolute h-full top-0 right-1 flex items-center px-2 text-muted-foreground text-xs font-medium select-none">
        {suffix}
      </span>
    </div>
  );
}

function switchMode (mode: KnowledgeBaseChunkingConfig['mode']): KnowledgeBaseChunkingConfig {
  switch (mode) {
    case 'general':
      return {
        mode: 'general',
        ...switchSplitter('SentenceSplitter'),
      };
    case 'advanced': {
      return {
        mode: 'advanced',
        rules: {
          'text/plain': {
            splitter: 'SentenceSplitter',
            splitter_config: switchSplitter('SentenceSplitter'),
          },
          'text/markdown': {
            splitter: 'MarkdownSplitter',
            splitter_config: switchSplitter('MarkdownSplitter'),
          },
        },
      };
    }
  }
}

function switchSplitter (splitter: 'SentenceSplitter'): KnowledgeBaseChunkingSentenceSplitterConfig;
function switchSplitter (splitter: 'MarkdownSplitter'): KnowledgeBaseChunkingMarkdownSplitterConfig;
function switchSplitter (splitter: 'SentenceSplitter' | 'MarkdownSplitter') {
  switch (splitter) {
    case 'SentenceSplitter':
      return {
        chunk_size: 1024,
        chunk_overlap: 200,
        paragraph_separator: '\\n\\n',
      } satisfies KnowledgeBaseChunkingSentenceSplitterConfig;
    case 'MarkdownSplitter':
      return {
        chunk_size: 1200,
        chunk_header_level: 2,
      } satisfies KnowledgeBaseChunkingMarkdownSplitterConfig;
  }
}

const defaultConfig = switchMode('general');
