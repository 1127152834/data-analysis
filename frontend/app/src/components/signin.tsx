'use client';

import { login } from '@/api/auth';
import { FormInput } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Form, formDomEventHandlers } from '@/components/ui/form.beta';
import { getErrorMessage } from '@/lib/errors';
import { useForm } from '@tanstack/react-form';
import { Loader2Icon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState, useTransition } from 'react';

const field = formFieldLayout<{
  username: string
  password: string
}>();

export function Signin ({ noRedirect = false, callbackUrl }: { noRedirect?: boolean, callbackUrl?: string }) {
  const [transitioning, startTransition] = useTransition();
  const router = useRouter();
  const [error, setError] = useState<string>();
  const form = useForm<{ username: string; password: string }>({
    defaultValues: {
      username: '',
      password: '',
    },
    onSubmit: async ({ value }) => {
      setError(undefined);
      try {
        await login(value);
        startTransition(() => {
          if (!noRedirect) {
            router.replace(refineCallbackUrl(callbackUrl));
          }
          router.refresh();
        });
      } catch (error) {
        setError(getErrorMessage(error));
      }
    },
  });

  const loading = form.state.isSubmitting || transitioning;

  return (
    <>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>
            登录失败
          </AlertTitle>
          <AlertDescription>
            无法使用提供的凭据登录。
          </AlertDescription>
        </Alert>
      )}
      <Form form={form} disabled={transitioning}>
        <form className="space-y-2" {...formDomEventHandlers(form, transitioning)}>
          <field.Basic name="username" label="用户名">
            <FormInput placeholder="x@example.com" />
          </field.Basic>
          <field.Basic name="password" label="密码">
            <FormInput type="password" />
          </field.Basic>
          <Button className="!mt-4 w-full" type="submit" disabled={loading}>
            {loading && <Loader2Icon className="w-4 h-4 mr-2 animate-spin repeat-infinite" />}
            {transitioning ? '重定向中...' : loading ? '登录中...' : '登录'}
          </Button>
        </form>
      </Form>
    </>
  );
}

function refineCallbackUrl (url: string | undefined) {
  if (!url) {
    return `${location.origin}`;
  }
  if (/auth\/login/.test(url)) {
    return `${location.origin}`;
  } else {
    return url;
  }
}
