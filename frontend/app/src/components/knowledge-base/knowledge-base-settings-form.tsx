'use client';

import { type KnowledgeBase, type KnowledgeBaseIndexMethod, type UpdateKnowledgeBaseParams, updateKnowledgeBase } from '@/api/knowledge-base';
import { EmbeddingModelSelect, LLMSelect } from '@/components/form/biz';
import { FormInput, FormSwitch, FormTextarea } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { mutateKnowledgeBases } from '@/components/knowledge-base/hooks';
import { KnowledgeBaseChunkingConfigFields } from '@/components/knowledge-base/knowledge-base-chunking-config-fields';
import { fieldAccessor, type GeneralSettingsFieldAccessor, GeneralSettingsForm, shallowPick } from '@/components/settings-form';
import { GeneralSettingsField as GeneralSettingsField } from '@/components/settings-form/GeneralSettingsField';
import type { KeyOfType } from '@/lib/typing-utils';
import { format } from 'date-fns';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { z } from 'zod';

const field = formFieldLayout<{ value: any }>();

export function KnowledgeBaseSettingsForm ({ knowledgeBase }: { knowledgeBase: KnowledgeBase }) {
  const router = useRouter();
  const [transitioning, startTransition] = useTransition();

  return (
    <GeneralSettingsForm
      data={knowledgeBase}
      readonly={false}
      loading={transitioning}
      onUpdate={async (data, path) => {
        if (['name', 'description', 'chunking_config'].includes(path[0] as never)) {
          const partial = shallowPick(data, path as never);
          
          // 处理chunking_config
          if (path[0] === 'chunking_config') {
            if (partial.chunking_config === null) {
              // 如果chunking_config是null，转换为undefined
              (partial as any).chunking_config = undefined;
            } else if (partial.chunking_config?.mode === 'advanced') {
              // 确保高级模式下有rules字段
              if (!partial.chunking_config.rules) {
                partial.chunking_config.rules = {
                  'text/plain': {
                    splitter: 'SentenceSplitter',
                    splitter_config: {
                      chunk_size: 1024,
                      chunk_overlap: 200,
                      paragraph_separator: '\\n\\n',
                    },
                  },
                  'text/markdown': {
                    splitter: 'MarkdownSplitter',
                    splitter_config: {
                      chunk_size: 1200,
                      chunk_header_level: 2,
                    },
                  },
                };
              }
            }
          }
          
          await updateKnowledgeBase(knowledgeBase.id, partial as UpdateKnowledgeBaseParams);
          startTransition(() => {
            router.refresh();
            mutateKnowledgeBases();
          });
        } else {
          throw new Error(`${path.map(p => String(p)).join('.')} is not updatable currently.`);
        }
      }}>
      <GeneralSettingsField schema={nameSchema} accessor={nameAccessor}>
        <field.Basic name="value" label="名称">
          <FormInput />
        </field.Basic>
      </GeneralSettingsField>
      <GeneralSettingsField schema={descriptionSchema} accessor={descriptionAccessor}>
        <field.Basic name="value" label="描述">
          <FormTextarea />
        </field.Basic>
      </GeneralSettingsField>
      <GeneralSettingsField readonly schema={llmSchema} accessor={llmAccessor}>
        <field.Basic name="value" label="大语言模型">
          <LLMSelect />
        </field.Basic>
      </GeneralSettingsField>
      <GeneralSettingsField readonly schema={embeddingModelSchema} accessor={embeddingModelAccessor}>
        <field.Basic name="value" label="嵌入模型">
          <EmbeddingModelSelect />
        </field.Basic>
      </GeneralSettingsField>
      <div className="space-y-2">
        <div className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">索引方法</div>
        <div className="space-y-2 pt-2">
          <GeneralSettingsField readonly accessor={vectorAccessor} schema={vectorSchema}>
            <field.Contained name="value" label="向量索引" description="使用向量嵌入来表示文档，以便可以基于其语义检索相关文档">
              <FormSwitch />
            </field.Contained>
          </GeneralSettingsField>
          <GeneralSettingsField readonly accessor={kgAccessor} schema={kgSchema}>
            <field.Contained name="value" label="知识图谱索引" description="从文档中提取实体和关系，并使用知识图谱表示，增强检索过程的逻辑和推理能力">
              <FormSwitch />
            </field.Contained>
          </GeneralSettingsField>
        </div>
      </div>
      <KnowledgeBaseChunkingConfigFields />
      <GeneralSettingsField readonly schema={createdAtSchema} accessor={createdAtAccessor}>
        <field.Basic name="value" label="创建时间">
          <FormInput />
        </field.Basic>
      </GeneralSettingsField>
      <GeneralSettingsField readonly schema={updatedAtSchema} accessor={updatedAtAccessor}>
        <field.Basic name="value" label="更新时间">
          <FormInput />
        </field.Basic>
      </GeneralSettingsField>
    </GeneralSettingsForm>
  );
}

const getIndexMethodAccessor = (method: KnowledgeBaseIndexMethod): GeneralSettingsFieldAccessor<KnowledgeBase, boolean> => ({
  path: ['index_methods'],
  get: data => data.index_methods.includes('vector'),
  set: (data, value) => {
    if (value) {
      return {
        ...data,
        index_methods: Array.from(new Set(data.index_methods.concat(method))),
      };
    } else {
      return {
        ...data,
        index_methods: data.index_methods.filter(m => m !== method),
      };
    }
  },
});
const getDatetimeAccessor = (key: KeyOfType<KnowledgeBase, Date>): GeneralSettingsFieldAccessor<KnowledgeBase, string> => {
  return {
    path: [key],
    get (data) {
      return format(data[key], 'yyyy-MM-dd HH:mm:ss');
    },
    set () {
      throw new Error(`update ${key} is not supported`);
    },
  };
};

const nameSchema = z.string();
const nameAccessor = fieldAccessor<KnowledgeBase, 'name'>('name');

const descriptionSchema = z.string();
const descriptionAccessor = fieldAccessor<KnowledgeBase, 'description'>('description');

const vectorSchema = z.boolean();
const vectorAccessor = getIndexMethodAccessor('vector');

const kgSchema = z.boolean();
const kgAccessor = getIndexMethodAccessor('knowledge_graph');

const llmSchema = z.number();
const llmAccessor: GeneralSettingsFieldAccessor<KnowledgeBase, number | undefined> = {
  path: ['llm'],
  get (data) {
    return data.llm?.id;
  },
  set () {
    throw new Error('TODO');
  },
};

const embeddingModelSchema = z.number();
const embeddingModelAccessor: GeneralSettingsFieldAccessor<KnowledgeBase, number | undefined> = {
  path: ['embedding_model'],
  get (data) {
    return data.embedding_model?.id;
  },
  set () {
    throw new Error('TODO');
  },
};

const createdAtSchema = z.string();
const createdAtAccessor = getDatetimeAccessor('created_at');

const updatedAtSchema = z.string();
const updatedAtAccessor = getDatetimeAccessor('updated_at');
