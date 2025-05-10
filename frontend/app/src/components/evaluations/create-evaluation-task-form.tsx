import { createEvaluationTask, type CreateEvaluationTaskParams } from '@/api/evaluations';
import { ChatEngineSelect, EvaluationDatasetSelect } from '@/components/form/biz';
import { FormInput } from '@/components/form/control-widget';
import { withCreateEntityForm as withCreateEntityForm } from '@/components/form/create-entity-form';
import { formFieldLayout } from '@/components/form/field-layout';
import type { ComponentProps } from 'react';
import { z, type ZodType } from 'zod';

const schema = z.object({
  name: z.string().min(1),
  evaluation_dataset_id: z.number().int(),
  chat_engine: z.string().optional(),
  run_size: z.coerce.number().int().min(1).optional(),
}) satisfies ZodType<CreateEvaluationTaskParams, any, any>;

const FormImpl = withCreateEntityForm(schema, createEvaluationTask);
const field = formFieldLayout<typeof schema>();

export function CreateEvaluationTaskForm ({ transitioning, onCreated }: Omit<ComponentProps<typeof FormImpl>, 'defaultValues' | 'children'>) {
  return (
    <FormImpl
      transitioning={transitioning}
      onCreated={onCreated}
    >
      <field.Basic name="name" label="名称" required defaultValue="">
        <FormInput />
      </field.Basic>
      <field.Basic name="evaluation_dataset_id" label="评估数据集" required>
        <EvaluationDatasetSelect />
      </field.Basic>
      <field.Basic name="chat_engine" label="聊天引擎">
        <ChatEngineSelect />
      </field.Basic>
      <field.Basic name="run_size" label="运行大小" description="要运行的评估数据集项目数量。默认运行整个数据集。">
        <FormInput type="number" min={1} step={1} />
      </field.Basic>
    </FormImpl>
  );
}
