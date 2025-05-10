import { createApiKey, type CreateApiKeyResponse } from '@/api/api-keys';
import { FormInput } from '@/components/form/control-widget';
import { withCreateEntityForm } from '@/components/form/create-entity-form';
import { z } from 'zod';

const schema = z.object({
  description: z.string(),
});

export interface CreateApiKeyFormProps {
  onCreated?: (data: CreateApiKeyResponse) => void;
}

const FormImpl = withCreateEntityForm(schema, createApiKey, {
  submitTitle: '创建API密钥',
  submittingTitle: '正在创建API密钥...',
});

export function CreateApiKeyForm ({ onCreated }: CreateApiKeyFormProps) {
  return (
    <FormImpl onCreated={onCreated}>
      <FormImpl.Basic name="description" label="API密钥描述">
        <FormInput />
      </FormImpl.Basic>
    </FormImpl>
  );
}
