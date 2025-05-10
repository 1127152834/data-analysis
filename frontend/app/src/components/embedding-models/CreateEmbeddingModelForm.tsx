'use client';

import { type CreateEmbeddingModel, createEmbeddingModel, type EmbeddingModel, testEmbeddingModel } from '@/api/embedding-models';
import { useEmbeddingModelProviders } from '@/components/embedding-models/hooks';
import { ProviderSelect } from '@/components/form/biz';
import { FormInput } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { FormRootError } from '@/components/form/root-error';
import { onSubmitHelper } from '@/components/form/utils';
import { CodeInput } from '@/components/form/widgets/CodeInput';
import { ProviderDescription } from '@/components/provider-description';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Form, formDomEventHandlers, FormSubmit } from '@/components/ui/form.beta';
import { useModelProvider } from '@/hooks/use-model-provider';
import { zodJsonText } from '@/lib/zod';
import { useForm } from '@tanstack/react-form';
import { useId, useState } from 'react';
import { toast } from 'sonner';
import { z } from 'zod';

const unsetForm = z.object({
  name: z.string().min(1, '不能为空'),
  provider: z.string().min(1, '不能为空'),
  vector_dimension: z.coerce.number().int().positive(),
  config: zodJsonText().optional(),
});

const strCredentialForm = unsetForm.extend({
  model: z.string().min(1, '不能为空'),
  credentials: z.string().min(1, '不能为空'),
});

const dictCredentialForm = unsetForm.extend({
  model: z.string().min(1, '不能为空'),
  credentials: zodJsonText(),
});

const field = formFieldLayout<CreateEmbeddingModel>();

export function CreateEmbeddingModelForm ({ transitioning, onCreated }: { transitioning?: boolean, onCreated?: (embeddingModel: EmbeddingModel) => void }) {
  const id = useId();
  const { data: options, isLoading, error } = useEmbeddingModelProviders();
  const [submissionError, setSubmissionError] = useState<unknown>();

  const form = useForm<CreateEmbeddingModel | Omit<CreateEmbeddingModel, 'model' | 'credentials'>>({
    validators: {
      onSubmit: unsetForm,
    },
    onSubmit (props) {
      const { value } = props;
      const provider = options?.find(option => option.provider === value.provider);

      const schema = provider
        ? provider.credentials_type === 'str'
          ? strCredentialForm
          : provider.credentials_type === 'dict'
            ? dictCredentialForm
            : unsetForm
        : unsetForm;

      return onSubmitHelper(schema, async (values) => {
        const { error, success } = await testEmbeddingModel(values as CreateEmbeddingModel);
        if (!success) {
          throw new Error(error || '测试嵌入模型失败');
        }
        const embeddingModel = await createEmbeddingModel(values as CreateEmbeddingModel);
        toast.success(`嵌入模型 ${embeddingModel.name} 创建成功。`);
        onCreated?.(embeddingModel);
      }, setSubmissionError)(props);
    },
    defaultValues: {
      name: '',
      provider: '',
      vector_dimension: 1536,
      config: '{}',
    },
  });

  const provider = useModelProvider(form, options, 'default_embedding_model');

  return (
    <>
      <Form form={form} disabled={transitioning} submissionError={submissionError}>
        <form id={id} className="space-y-4 max-w-screen-sm" {...formDomEventHandlers(form, transitioning)}>
          <field.Basic name="name" label="名称">
            <FormInput />
          </field.Basic>
          <field.Basic name="provider" label="提供商" description={provider && <ProviderDescription provider={provider} />}>
            <ProviderSelect options={options} isLoading={isLoading} error={error} />
          </field.Basic>
          {provider && (
            <>
              <field.Basic name="model" label="模型" description={provider.embedding_model_description}>
                <FormInput />
              </field.Basic>
              <field.Basic name="credentials" label={provider.credentials_display_name} description={provider.credentials_description}>
                {provider.credentials_type === 'str'
                  ? <FormInput placeholder={provider.default_credentials} />
                  : <CodeInput language="json" placeholder={JSON.stringify(provider.default_credentials, undefined, 2)} />
                }
              </field.Basic>
              <field.Basic name="vector_dimension" label="向量维度">
                <FormInput type="number" min={1} />
              </field.Basic>
              <Accordion type="multiple">
                <AccordionItem value="advanced-settings">
                  <AccordionTrigger>
                    高级设置
                  </AccordionTrigger>
                  <AccordionContent className="px-4">
                    <field.Basic name="config" label="配置" description={provider.config_description}>
                      <CodeInput language="json" />
                    </field.Basic>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </>
          )}
          <FormRootError title="创建嵌入模型失败" />
          <FormSubmit disabled={!options} transitioning={transitioning} form={id}>
            创建嵌入模型
          </FormSubmit>
        </form>
      </Form>
    </>
  );
}
