'use client';

import { type ChatEngine, type ChatEngineKnowledgeGraphOptions, type ChatEngineLLMOptions, type ChatEngineOptions, updateChatEngine } from '@/api/chat-engines';
import { KBListSelect } from '@/components/chat-engine/kb-list-select';
import { LLMSelect, RerankerSelect } from '@/components/form/biz';
import { FormCheckbox, FormInput, FormSwitch } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { PromptInput } from '@/components/form/widgets/PromptInput';
import { SecondaryNavigatorItem, SecondaryNavigatorLayout, SecondaryNavigatorList, SecondaryNavigatorMain } from '@/components/secondary-navigator-list';
import { fieldAccessor, GeneralSettingsField as GeneralSettingsField, type GeneralSettingsFieldAccessor, GeneralSettingsForm, shallowPick } from '@/components/settings-form';
import type { KeyOfType } from '@/lib/typing-utils';
import { capitalCase } from 'change-case-all';
import { format } from 'date-fns';
import { useRouter } from 'next/navigation';
import { type ReactNode, useTransition } from 'react';
import { z } from 'zod';

const field = formFieldLayout<{ value: any | any[] }>();

export function UpdateChatEngineForm ({ chatEngine, defaultChatEngineOptions }: { chatEngine: ChatEngine, defaultChatEngineOptions: ChatEngineOptions }) {
  const [transitioning, startTransition] = useTransition();
  const router = useRouter();

  return (
    <GeneralSettingsForm
      data={chatEngine}
      readonly={false}
      loading={transitioning}
      onUpdate={async (data, path) => {
        if (updatableFields.includes(path[0] as any)) {
          const partial = shallowPick(data, path as [(typeof updatableFields)[number], ...any[]]);
          await updateChatEngine(chatEngine.id, partial);
          startTransition(() => {
            router.refresh();
          });
        } else {
          throw new Error(`${path.map(p => String(p)).join('.')} is not updatable currently.`);
        }
      }}
    >
      <SecondaryNavigatorLayout defaultValue="常规">
        <SecondaryNavigatorList>
          <SecondaryNavigatorItem value="常规">
            常规
          </SecondaryNavigatorItem>
          <SecondaryNavigatorItem value="检索">
            检索
          </SecondaryNavigatorItem>
          <SecondaryNavigatorItem value="生成">
            生成
          </SecondaryNavigatorItem>
          <SecondaryNavigatorItem value="实验性">
            实验性
          </SecondaryNavigatorItem>
          <div className="mt-auto pt-2 text-xs text-gray-500 space-y-1">
            <div className="flex justify-between px-3">
              <span>创建时间:</span>
              <span>{format(chatEngine.created_at, 'yyyy-MM-dd HH:mm:ss')}</span>
            </div>
            <div className="flex justify-between px-3">
              <span>更新时间:</span>
              <span>{format(chatEngine.updated_at, 'yyyy-MM-dd HH:mm:ss')}</span>
            </div>
          </div>
        </SecondaryNavigatorList>
        <Section title="常规">
          <GeneralSettingsField accessor={nameAccessor} schema={nameSchema}>
            <field.Basic name="value" label="名称">
              <FormInput placeholder="输入聊天引擎名称" />
            </field.Basic>
          </GeneralSettingsField>
          <GeneralSettingsField accessor={isDefaultAccessor} schema={isDefaultSchema}>
            <field.Contained unimportant name="value" label="默认引擎" fallbackValue={chatEngine.is_default} description="将此聊天引擎设为新对话的默认引擎">
              <FormSwitch />
            </field.Contained>
          </GeneralSettingsField>
          <SubSection title="模型">
            <GeneralSettingsField accessor={llmIdAccessor} schema={idSchema}>
              <field.Basic name="value" label="大语言模型">
                <LLMSelect />
              </field.Basic>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={fastLlmIdAccessor} schema={idSchema}>
              <field.Basic name="value" label="快速语言模型">
                <LLMSelect />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
        </Section>

        <Section title="检索">
          <SubSection title="知识源">
            <GeneralSettingsField accessor={kbAccessor} schema={kbSchema}>
              <field.Basic required name="value" label="知识库">
                <KBListSelect />
              </field.Basic>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={hideSourcesAccessor} schema={hideSourcesSchema}>
              <field.Inline name="value" label="隐藏来源" fallbackValue={defaultChatEngineOptions.hide_sources} description="在聊天响应中隐藏知识来源">
                <FormCheckbox />
              </field.Inline>
            </GeneralSettingsField>
          </SubSection>
          <SubSection title="语义搜索">
            <GeneralSettingsField accessor={rerankerIdAccessor} schema={idSchema}>
              <field.Basic name="value" label="重排序器">
                <RerankerSelect />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
          <SubSection title="知识图谱">
            <GeneralSettingsField accessor={kgEnabledAccessor} schema={kgEnabledSchema}>
              <field.Contained name="value" label="启用知识图谱" fallbackValue={defaultChatEngineOptions.knowledge_graph?.enabled} description="启用知识图谱以丰富上下文信息">
                <FormSwitch />
              </field.Contained>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={kgDepthAccessor} schema={kgDepthSchema}>
              <field.Basic name="value" label="深度" fallbackValue={defaultChatEngineOptions.knowledge_graph?.depth} description="设置知识图谱搜索的最大遍历深度（较高的值允许找到更远的关系）">
                <FormInput type="number" min={1} />
              </field.Basic>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={kgIncludeMetaAccessor} schema={kgIncludeMetaSchema}>
              <field.Inline name="value" label="包含元数据" fallbackValue={defaultChatEngineOptions.knowledge_graph?.include_meta} description="在知识图谱节点中包含元数据信息，以提供额外上下文">
                <FormCheckbox />
              </field.Inline>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={kgWithDegreeAccessor} schema={kgWithDegreeSchema}>
              <field.Inline name="value" label="包含度数信息" fallbackValue={defaultChatEngineOptions.knowledge_graph?.with_degree} description="在知识图谱中包含实体的入度和出度信息，用于权重计算和排名">
                <FormCheckbox />
              </field.Inline>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={kgUsingIntentSearchAccessor} schema={kgUsingIntentSearchSchema}>
              <field.Inline name="value" label="使用意图搜索" fallbackValue={defaultChatEngineOptions.knowledge_graph?.using_intent_search} description="启用智能搜索，将用户问题分解为子问题，以获得更全面的搜索结果">
                <FormCheckbox />
              </field.Inline>
            </GeneralSettingsField>
            {(['intent_graph_knowledge', 'normal_graph_knowledge'] as const).map(type => (
              <GeneralSettingsField key={type} accessor={llmAccessor[type]} schema={llmSchema}>
                <field.Basic name="value" label={capitalCase(type) === 'Intent Graph Knowledge' ? '意图图谱知识Prompt' : '常规图谱知识Prompt'} description="用于处理和提取基于图谱遍历方法的知识的模板" fallbackValue={defaultChatEngineOptions.llm?.[type]}>
                  <PromptInput />
                </field.Basic>
              </GeneralSettingsField>
            ))}
          </SubSection>
        </Section>

        <Section title="生成">
          <SubSection title="明确问题">
            <GeneralSettingsField accessor={clarifyAccessor} schema={clarifyAccessorSchema}>
              <field.Contained unimportant name="value" label="明确问题" fallbackValue={defaultChatEngineOptions.clarify_question} description="允许聊天机器人检查用户输入是否模糊并提出澄清问题">
                <FormSwitch />
              </field.Contained>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={llmAccessor.clarifying_question_prompt} schema={llmSchema}>
              <field.Basic name="value" label="明确问题Prompt" description="当用户的输入需要更多上下文或具体信息时，用于生成澄清问题的提示模板" fallbackValue={defaultChatEngineOptions.llm?.clarifying_question_prompt}>
                <PromptInput />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
          <SubSection title="重写问题">
            <GeneralSettingsField accessor={llmAccessor.condense_question_prompt} schema={llmSchema}>
              <field.Basic name="value" label="问题重写Prompt" description={promptDescriptions.condense_question_prompt} fallbackValue={defaultChatEngineOptions.llm?.condense_question_prompt}>
                <PromptInput />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
          <SubSection title="回答问题">
            <GeneralSettingsField accessor={llmAccessor.text_qa_prompt} schema={llmSchema}>
              <field.Basic name="value" label="回答问题Prompt" description={promptDescriptions.text_qa_prompt} fallbackValue={defaultChatEngineOptions.llm?.text_qa_prompt}>
                <PromptInput />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
          <SubSection title="延伸问题">
            <GeneralSettingsField accessor={optionAccessor('further_questions')} schema={z.boolean().nullable().optional()}>
              <field.Contained
                unimportant
                name="value"
                label="显示延伸问题"
                fallbackValue={defaultChatEngineOptions.further_questions}
                description="每个回答后显示建议的跟进问题"
              >
                <FormSwitch />
              </field.Contained>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={llmAccessor.further_questions_prompt} schema={llmSchema}>
              <field.Basic name="value" label="延伸问题Prompt" description="生成后续问题以继续对话的模板" fallbackValue={defaultChatEngineOptions.llm?.further_questions_prompt}>
                <PromptInput />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
        </Section>

        <Section title="实验性">
          <SubSection title="外部引擎">
            <GeneralSettingsField accessor={externalEngineAccessor} schema={externalEngineSchema}>
              <field.Basic name="value" label="外部聊天引擎URL" fallbackValue={defaultChatEngineOptions.external_engine_config?.stream_chat_api_url ?? ''}>
                <FormInput placeholder="输入引擎地址" />
              </field.Basic>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={llmAccessor.generate_goal_prompt} schema={llmSchema}>
              <field.Basic name="value" label="目标生成Prompt" description="根据用户输入生成会话目标和目的的模板" fallbackValue={defaultChatEngineOptions.llm?.generate_goal_prompt}>
                <PromptInput />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
          <SubSection title="验证服务">
            <GeneralSettingsField accessor={postVerificationUrlAccessor} schema={postVerificationUrlSchema}>
              <field.Basic name="value" label="验证服务URL" fallbackValue={defaultChatEngineOptions.post_verification_url ?? ''}>
                <FormInput placeholder="输入验证服务地址" />
              </field.Basic>
            </GeneralSettingsField>
            <GeneralSettingsField accessor={postVerificationTokenAccessor} schema={postVerificationTokenSchema}>
              <field.Basic name="value" label="验证服务令牌" fallbackValue={defaultChatEngineOptions.post_verification_token ?? ''}>
                <FormInput placeholder="输入验证服务令牌" />
              </field.Basic>
            </GeneralSettingsField>
          </SubSection>
        </Section>
      </SecondaryNavigatorLayout>
    </GeneralSettingsForm>
  );
}

const updatableFields = ['name', 'llm_id', 'fast_llm_id', 'reranker_id', 'engine_options', 'is_default'] as const;

function optionAccessor<K extends keyof ChatEngineOptions> (key: K): GeneralSettingsFieldAccessor<ChatEngine, ChatEngineOptions[K]> {
  return {
    path: ['engine_options', key],
    get (engine) {
      return engine.engine_options[key];
    },
    set (engine, value) {
      return {
        ...engine,
        engine_options: {
          ...engine.engine_options,
          [key]: value,
        },
      };
    },
  };
}

function kgOptionAccessor<K extends keyof ChatEngineKnowledgeGraphOptions> (key: K): GeneralSettingsFieldAccessor<ChatEngine, ChatEngineKnowledgeGraphOptions[K]> {
  return {
    path: ['engine_options', 'knowledge_graph', key],
    get (engine) {
      return engine.engine_options.knowledge_graph?.[key];
    },
    set (engine, value) {
      return {
        ...engine,
        engine_options: {
          ...engine.engine_options,
          knowledge_graph: {
            ...engine.engine_options.knowledge_graph,
            [key]: value,
          },
        },
      };
    },
  };
}

function llmOptionAccessor<K extends keyof ChatEngineLLMOptions> (key: K): GeneralSettingsFieldAccessor<ChatEngine, ChatEngineLLMOptions[K]> {
  return {
    path: ['engine_options', 'llm', key],
    get (engine) {
      return engine.engine_options.llm?.[key];
    },
    set (engine, value) {
      return {
        ...engine,
        engine_options: {
          ...engine.engine_options,
          llm: {
            ...engine.engine_options.llm,
            [key]: value,
          },
        },
      };
    },
  };
}

const getDatetimeAccessor = (key: KeyOfType<ChatEngine, Date>): GeneralSettingsFieldAccessor<ChatEngine, string> => {
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

const idAccessor = fieldAccessor<ChatEngine, 'id'>('id');

const createdAccessor = getDatetimeAccessor('created_at');
const updatedAccessor = getDatetimeAccessor('updated_at');
const neverSchema = z.never();

const nameAccessor = fieldAccessor<ChatEngine, 'name'>('name');
const nameSchema = z.string().min(1);

const clarifyAccessor = optionAccessor('clarify_question');
const clarifyAccessorSchema = z.boolean().nullable().optional();

const isDefaultAccessor = fieldAccessor<ChatEngine, 'is_default'>('is_default');
const isDefaultSchema = z.boolean();

const getIdAccessor = (id: KeyOfType<ChatEngine, number | null>) => fieldAccessor<ChatEngine, KeyOfType<ChatEngine, number | null>>(id);
const idSchema = z.number().nullable();
const llmIdAccessor = getIdAccessor('llm_id');
const fastLlmIdAccessor = getIdAccessor('fast_llm_id');
const rerankerIdAccessor = getIdAccessor('reranker_id');

const kbAccessor: GeneralSettingsFieldAccessor<ChatEngine, number[] | null> = {
  path: ['engine_options'],
  get (data) {
    console.log(data.engine_options.knowledge_base?.linked_knowledge_bases?.map(kb => kb.id) ?? null);
    return data.engine_options.knowledge_base?.linked_knowledge_bases?.map(kb => kb.id) ?? null;
  },
  set (data, value) {
    return {
      ...data,
      engine_options: {
        ...data.engine_options,
        knowledge_base: {
          linked_knowledge_base: undefined,
          linked_knowledge_bases: value?.map(id => ({ id })) ?? null,
        },
      },
    };
  },
};
const kbSchema = z.number().array().min(1);

const kgEnabledAccessor = kgOptionAccessor('enabled');
const kgEnabledSchema = z.boolean().nullable();

const kgWithDegreeAccessor = kgOptionAccessor('with_degree');
const kgWithDegreeSchema = z.boolean().nullable();

const kgIncludeMetaAccessor = kgOptionAccessor('include_meta');
const kgIncludeMetaSchema = z.boolean().nullable();

const kgUsingIntentSearchAccessor = kgOptionAccessor('using_intent_search');
const kgUsingIntentSearchSchema = z.boolean().nullable();

const kgDepthAccessor = kgOptionAccessor('depth');
const kgDepthSchema = z.number().int().min(1).nullable();

const hideSourcesAccessor = optionAccessor('hide_sources');
const hideSourcesSchema = z.boolean().nullable();

const llmPromptFields = [
  'condense_question_prompt',
  'text_qa_prompt',
  'intent_graph_knowledge',
  'normal_graph_knowledge',
  'clarifying_question_prompt',
  'generate_goal_prompt',
  'further_questions_prompt',
] as const;

const llmAccessor: { [P in (typeof llmPromptFields[number])]: GeneralSettingsFieldAccessor<ChatEngine, string | null> } = Object.fromEntries(llmPromptFields.map(name => [name, llmOptionAccessor(name)])) as never;
const llmSchema = z.string().nullable();

const postVerificationUrlAccessor = optionAccessor('post_verification_url');
const postVerificationUrlSchema = z.string().nullable();

const postVerificationTokenAccessor = optionAccessor('post_verification_token');
const postVerificationTokenSchema = z.string().nullable();

const externalEngineAccessor: GeneralSettingsFieldAccessor<ChatEngine, string | null> = {
  path: ['engine_options'],
  get (engine) {
    return engine.engine_options.external_engine_config?.stream_chat_api_url ?? null;
  },
  set (engine, value) {
    return {
      ...engine,
      engine_options: {
        ...engine.engine_options,
        external_engine_config: {
          stream_chat_api_url: value,
        },
      },
    };
  },
};
const externalEngineSchema = z.string().nullable();

function Section ({ title, children }: { title: string, children: ReactNode }) {
  return (
    <>
      <SecondaryNavigatorMain className="max-w-screen-sm space-y-8 px-2 pb-8" value={title} strategy="mount">
        {children}
      </SecondaryNavigatorMain>
    </>
  );
}

function SubSection ({ title, children }: { title: ReactNode, children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h4 className="text-lg">{title}</h4>
      {children}
    </section>
  );
}

const promptDescriptions: Record<typeof llmPromptFields[number], string> = {
  'condense_question_prompt': '将对话历史和后续问题浓缩为独立问题的提示模板',
  'text_qa_prompt': '根据提供的上下文和问题生成答案的提示模板',
  'intent_graph_knowledge': '用于处理和提取基于图谱遍历方法的知识的模板',
  'normal_graph_knowledge': '用于处理和提取基于图谱遍历方法的知识的模板',
  'clarifying_question_prompt': '当用户的输入需要更多上下文或具体信息时，用于生成澄清问题的提示模板',
  'generate_goal_prompt': '根据用户输入生成会话目标和目的的模板',
  'further_questions_prompt': '生成后续问题以继续对话的模板',
};
