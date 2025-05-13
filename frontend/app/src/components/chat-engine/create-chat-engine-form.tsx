'use client';

import { type ChatEngineOptions, createChatEngine } from '@/api/chat-engines';
import { KBListSelectForObjectValue } from '@/components/chat-engine/kb-list-select';
import { DBListSelectForObjectValue } from '@/components/chat-engine/db-list-select';
import { FormSection, FormSectionsProvider, useFormSectionFields } from '@/components/form-sections';
import { LLMSelect, RerankerSelect } from '@/components/form/biz';
import { FormCheckbox, FormInput, FormSwitch } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { FormRootError } from '@/components/form/root-error';
import { onSubmitHelper } from '@/components/form/utils';
import { PromptInput } from '@/components/form/widgets/PromptInput';
import { SecondaryNavigatorItem, SecondaryNavigatorLayout, SecondaryNavigatorList, SecondaryNavigatorMain } from '@/components/secondary-navigator-list';
import { Button } from '@/components/ui/button';
import { Form, formDomEventHandlers, useFormContext } from '@/components/ui/form.beta';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';
import { useForm } from '@tanstack/react-form';
import { capitalCase } from 'change-case-all';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect, useId, useState, useTransition } from 'react';
import { toast } from 'sonner';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(1),
  llm_id: z.number().optional(),
  fast_llm_id: z.number().optional(),
  reranker_id: z.number().optional(),
  engine_options: z.object({
    knowledge_base: z.object({
      linked_knowledge_bases: z.object({
        id: z.number(),
      }).array().min(1),
    }),
    database_sources: z.object({
      id: z.number(),
    }).array().optional(),
    knowledge_graph: z.object({
      depth: z.number().min(1).nullable().optional(),
    }).passthrough().optional(),
    llm: z.object({}).passthrough().optional(),
  }).passthrough(),
});

const field = formFieldLayout<typeof schema>();

const nameSchema = z.string().min(1);
const kbSchema = z.object({ id: z.number() }).array().min(1);
const kgGraphDepthSchema = z.number().min(1).optional();

export function CreateChatEngineForm ({ defaultChatEngineOptions }: { defaultChatEngineOptions: ChatEngineOptions }) {
  const [transitioning, startTransition] = useTransition();
  const [submissionError, setSubmissionError] = useState<unknown>(undefined);
  const router = useRouter();
  const id = useId();

  const form = useForm({
    onSubmit: onSubmitHelper(schema, async data => {
      const ce = await createChatEngine(data);
      startTransition(() => {
        router.push(`/chat-engines/${ce.id}`);
        router.refresh();
      });
    }, setSubmissionError),
    onSubmitInvalid () {
      toast.error('验证失败', { description: '请检查您的聊天引擎配置。' });
    },
  });

  return (
    <Form form={form} disabled={transitioning} submissionError={submissionError}>
      <FormSectionsProvider>
        <form id={id} {...formDomEventHandlers(form, transitioning)}>
          <SecondaryNavigatorLayout defaultValue="常规">
            <SecondaryNavigatorList>
              <SectionTabTrigger required value="常规" />
              <SectionTabTrigger required value="检索" />
              <SectionTabTrigger value="生成" />
              <SectionTabTrigger value="实验性" />
              <Separator />
              <FormRootError />
              <Button className="w-full" type="submit" form={id} disabled={form.state.isSubmitting || transitioning}>
                创建聊天引擎
              </Button>
            </SecondaryNavigatorList>

            <Section title="常规">
              <field.Basic required name="name" label="名称" defaultValue="" validators={{ onSubmit: nameSchema, onBlur: nameSchema }}>
                <FormInput placeholder="输入聊天引擎名称" />
              </field.Basic>
              <SubSection title="模型">
                <field.Basic name="llm_id" label="大语言模型">
                  <LLMSelect />
                </field.Basic>
                <field.Basic name="fast_llm_id" label="快速大语言模型">
                  <LLMSelect />
                </field.Basic>
              </SubSection>
            </Section>

            <Section title="检索">
              <SubSection title="知识源">
                <field.Basic
                  required
                  name="engine_options.knowledge_base.linked_knowledge_bases"
                  label="知识库"
                  validators={{ onChange: kbSchema, onSubmit: kbSchema }}
                >
                  <KBListSelectForObjectValue />
                </field.Basic>
                <field.Basic
                  name="engine_options.database_sources"
                  label="数据库源"
                >
                  <DBListSelectForObjectValue />
                </field.Basic>
                <field.Inline
                  name="engine_options.hide_sources"
                  label="隐藏源"
                  description="在聊天回复中隐藏知识源"
                  defaultValue={defaultChatEngineOptions.hide_sources}
                >
                  <FormCheckbox />
                </field.Inline>
              </SubSection>
              <SubSection title="语义搜索">
                <field.Basic name="reranker_id" label="重排序器">
                  <RerankerSelect />
                </field.Basic>
              </SubSection>
              <SubSection title="知识图谱">
                <field.Contained
                  name="engine_options.knowledge_graph.enabled"
                  label="启用知识图谱"
                  description="启用知识图谱以丰富上下文信息"
                  defaultValue={defaultChatEngineOptions.knowledge_graph?.enabled}
                >
                  <FormSwitch />
                </field.Contained>
                <field.Basic name="engine_options.knowledge_graph.depth" label="深度" fallbackValue={defaultChatEngineOptions.knowledge_graph?.depth} validators={{ onBlur: kgGraphDepthSchema, onSubmit: kgGraphDepthSchema }}>
                  <FormInput type="number" min={1} step={1} />
                </field.Basic>
                <field.Inline name="engine_options.knowledge_graph.include_meta" label="包含元数据" fallbackValue={defaultChatEngineOptions.knowledge_graph?.include_meta} description="在知识图谱节点中包含元数据信息以提供额外上下文">
                  <FormCheckbox />
                </field.Inline>
                <field.Inline name="engine_options.knowledge_graph.with_degree" label="包含度数信息" fallbackValue={defaultChatEngineOptions.knowledge_graph?.with_degree} description="在知识图谱中包含实体的入度和出度信息，用于权重计算和排名">
                  <FormCheckbox />
                </field.Inline>
                <field.Inline name="engine_options.knowledge_graph.using_intent_search" label="使用意图搜索" fallbackValue={defaultChatEngineOptions.knowledge_graph?.using_intent_search} description="启用智能搜索，将用户问题分解为子问题，以获得更全面的搜索结果">
                  <FormCheckbox />
                </field.Inline>
                {(['intent_graph_knowledge', 'normal_graph_knowledge'] as const).map(name => (
                  <field.Basic key={name} name={`engine_options.llm.${name}`} label={name === 'intent_graph_knowledge' ? '意图图谱知识Prompt' : '常规图谱知识Prompt'} fallbackValue={defaultChatEngineOptions.llm?.[name]} description={llmPromptDescriptions[name]}>
                    <PromptInput />
                  </field.Basic>
                ))}
              </SubSection>
            </Section>

            <Section title="生成">
              <SubSection title="明确问题">
                <field.Contained
                  unimportant
                  name="engine_options.clarify_question"
                  label="明确问题"
                  description="允许聊天机器人检查用户输入是否模糊并提出澄清问题"
                  defaultValue={defaultChatEngineOptions.clarify_question}
                >
                  <FormSwitch />
                </field.Contained>
                <field.Basic name="engine_options.llm.clarifying_question_prompt" label="明确问题Prompt" fallbackValue={defaultChatEngineOptions.llm?.clarifying_question_prompt} description={llmPromptDescriptions.clarifying_question_prompt}>
                  <PromptInput />
                </field.Basic>
              </SubSection>
              <SubSection title="重写问题">
                <field.Basic name="engine_options.llm.condense_question_prompt" label="问题重写Prompt" fallbackValue={defaultChatEngineOptions.llm?.condense_question_prompt} description={llmPromptDescriptions.condense_question_prompt}>
                  <PromptInput />
                </field.Basic>
              </SubSection>
              <SubSection title="回答问题">
                <field.Basic name="engine_options.llm.text_qa_prompt" label="回答问题Prompt" fallbackValue={defaultChatEngineOptions.llm?.text_qa_prompt} description={llmPromptDescriptions.text_qa_prompt}>
                  <PromptInput />
                </field.Basic>
              </SubSection>
              <SubSection title="延伸问题">
                <field.Contained
                  unimportant
                  name="engine_options.further_questions"
                  label="显示延伸问题"
                  description="在每个回答后显示建议的跟进问题"
                  defaultValue={defaultChatEngineOptions.further_questions}
                >
                  <FormSwitch />
                </field.Contained>
                <field.Basic name="engine_options.llm.further_questions_prompt" label="延伸问题Prompt" fallbackValue={defaultChatEngineOptions.llm?.further_questions_prompt} description={llmPromptDescriptions.further_questions_prompt}>
                  <PromptInput />
                </field.Basic>
              </SubSection>
            </Section>

            <Section title="实验性">
              <SubSection title="外部引擎">
                <field.Basic name="engine_options.external_engine_config.stream_chat_api_url" label="外部聊天引擎URL" fallbackValue={defaultChatEngineOptions.external_engine_config?.stream_chat_api_url ?? ''}>
                  <FormInput placeholder="输入引擎地址" />
                </field.Basic>
                <field.Basic name="engine_options.llm.generate_goal_prompt" label="目标生成Prompt" fallbackValue={defaultChatEngineOptions.llm?.generate_goal_prompt} description={llmPromptDescriptions.generate_goal_prompt}>
                  <PromptInput />
                </field.Basic>
              </SubSection>
              <SubSection title="验证服务">
                <field.Basic name="engine_options.post_verification_url" label="验证服务URL" fallbackValue={defaultChatEngineOptions.post_verification_url ?? ''}>
                  <FormInput placeholder="输入验证服务地址" />
                </field.Basic>
                <field.Basic name="engine_options.post_verification_token" label="验证服务令牌" fallbackValue={defaultChatEngineOptions.post_verification_token ?? ''}>
                  <FormInput placeholder="输入验证服务令牌" />
                </field.Basic>
              </SubSection>
            </Section>
          </SecondaryNavigatorLayout>
        </form>
      </FormSectionsProvider>
    </Form>
  );
}

function SectionTabTrigger ({ value, required }: { value: string, required?: boolean }) {
  const [invalid, setInvalid] = useState(false);
  const { form } = useFormContext();
  const fields = useFormSectionFields(value);

  useEffect(() => {
    return form.store.subscribe(() => {
      let invalid = false;
      for (let field of fields.values()) {
        if (field.getMeta().errors.length > 0) {
          invalid = true;
          break;
        }
      }
      setInvalid(invalid);
    });
  }, [form, fields, value]);

  return (
    <SecondaryNavigatorItem value={value}>
      <span className={cn(invalid && 'text-destructive')}>
        {value}
      </span>
      {required && <sup className="text-destructive" aria-hidden>*</sup>}
    </SecondaryNavigatorItem>
  );
}

function Section ({ title, children }: { title: string, children: ReactNode }) {
  return (
    <FormSection value={title}>
      <SecondaryNavigatorMain className="space-y-8 max-w-screen-sm px-2 pb-8" value={title} strategy="hidden">
        {children}
      </SecondaryNavigatorMain>
    </FormSection>
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

const llmPromptFields = [
  'condense_question_prompt',
  'text_qa_prompt',
  'intent_graph_knowledge',
  'normal_graph_knowledge',
  'clarifying_question_prompt',
  'generate_goal_prompt',
  'further_questions_prompt',
] as const;

const llmPromptDescriptions: { [P in typeof llmPromptFields[number]]: string } = {
  'condense_question_prompt': '将对话历史和后续问题浓缩为独立问题的提示模板',
  'text_qa_prompt': '根据提供的上下文和问题生成答案的提示模板',
  'intent_graph_knowledge': '用于处理和提取基于图谱遍历方法的知识的模板',
  'normal_graph_knowledge': '用于处理和提取基于图谱遍历方法的知识的模板',
  'clarifying_question_prompt': '当用户的输入需要更多上下文或具体信息时，用于生成澄清问题的提示模板',
  'generate_goal_prompt': '根据用户输入生成会话目标和目的的模板',
  'further_questions_prompt': '生成后续问题以继续对话的模板',
}; 