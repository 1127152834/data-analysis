import { createKnowledgeBase } from '@/api/knowledge-base';
import { EmbeddingModelSelect, LLMSelect } from '@/components/form/biz';
import { FormInput, FormTextarea } from '@/components/form/control-widget';
import { withCreateEntityForm } from '@/components/form/create-entity-form';
import { FormIndexMethods } from '@/components/knowledge-base/form-index-methods';
import { mutateKnowledgeBases } from '@/components/knowledge-base/hooks';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { z } from 'zod';

const Form = withCreateEntityForm(z.object({
  name: z.string().min(1),
  description: z.string(),
  index_methods: z.enum(['knowledge_graph', 'vector']).array(),
  llm_id: z.number().nullable().optional(),
  embedding_model_id: z.number().nullable().optional(),
  data_sources: z.never().array().length(0), // Use external page to create data source.
}), createKnowledgeBase);

export function CreateKnowledgeBaseForm ({}: {}) {
  const [transitioning, startTransition] = useTransition();
  const router = useRouter();

  return (
    <Form
      transitioning={transitioning}
      onCreated={kb => {
        startTransition(() => {
          router.push(`/knowledge-bases/${kb.id}/data-sources`);
          router.refresh();
        });
        void mutateKnowledgeBases();
      }}
      defaultValues={{
        name: '',
        description: '',
        llm_id: undefined,
        data_sources: [],
        embedding_model_id: undefined,
        index_methods: ['vector'],
      }}
    >
      <Form.Basic name="name" label="名称">
        <FormInput placeholder="知识库的名称" />
      </Form.Basic>
      <Form.Basic name="description" label="描述">
        <FormTextarea placeholder="知识库的描述" />
      </Form.Basic>
      <Form.Basic name="llm_id" label="大语言模型" description="指定用于构建索引的大语言模型。如果未指定，将使用默认模型。">
        <LLMSelect />
      </Form.Basic>
      <Form.Basic name="embedding_model_id" label="嵌入模型" description="指定用于将语料库转换为向量嵌入的模型。如果未指定，将使用默认模型。">
        <EmbeddingModelSelect />
      </Form.Basic>
      <Form.Basic name="index_methods" label="索引方法">
        <FormIndexMethods />
      </Form.Basic>
    </Form>
  );
}
