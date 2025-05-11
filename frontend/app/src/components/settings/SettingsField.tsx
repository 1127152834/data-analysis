import { type SettingItem, updateSiteSetting } from '@/api/site-settings';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { getErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import { zodResolver } from '@hookform/resolvers/zod';
import { capitalCase } from 'change-case-all';
import { deepEqual } from 'fast-equals';
import { CheckIcon, Loader2Icon, TriangleAlertIcon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { cloneElement, type ReactElement, type ReactNode, useCallback, useDeferredValue, useMemo, useTransition, useState } from 'react';
import { type ControllerRenderProps, useForm, useFormState, useWatch } from 'react-hook-form';
import { toast } from 'sonner';
import { z, type ZodType } from 'zod';
import { getErrorMessage as getErrorMessageBeta } from '@/lib/errors';
import { Form as FormBeta } from '@/components/ui/form.beta';
import { useForm as useFormTanstack } from '@tanstack/react-form';
import { ImageUploadInput } from '@/components/form/widgets/ImageUploadInput';

// 图片URL的正则表达式，用于判断值是否可能是图片URL
const IMAGE_URL_REGEX = /\.(jpg|jpeg|png|gif|svg|webp)($|\?)/i;

export interface SettingsFieldProps {
  name: string;
  item: SettingItem;
  arrayItemSchema?: ZodType;
  objectSchema?: ZodType;
  onChanged?: () => void;
  disabled?: boolean;
  children?: (props: ControllerRenderProps) => ReactElement<any>;
  displayName?: string;
}

/**
 * @deprecated
 */
export function SettingsField ({ name, item, arrayItemSchema, objectSchema, onChanged, disabled, children, displayName }: SettingsFieldProps) {
  const router = useRouter();
  const [transitioning, startTransition] = useTransition();
  const [error, setError] = useState<Error | null>(null);

  if (!item) {
    return (
      <Alert variant="warning">
        <TriangleAlertIcon />
        <AlertTitle>加载 <em>{name}</em> 失败</AlertTitle>
        <AlertDescription>前端和后端服务可能配置错误，请检查您的部署。</AlertDescription>
      </Alert>
    );
  }

  if (item.data_type === 'list') {
    if (!arrayItemSchema) {
      throw new Error(`list item requires array item schema`);
    }
  }

  if (item.data_type === 'dict') {
    if (!objectSchema) {
      throw new Error(`dict item requires object schema`);
    }
  }

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const schema = useMemo(() => {
    let schema: ZodType;
    switch (item.data_type) {
      case 'str':
        schema = z.string();
        break;
      case 'bool':
        schema = z.coerce.boolean();
        break;
      case 'int':
        schema = z.coerce.number().int();
        break;
      case 'float':
        schema = z.coerce.number();
        break;
      case 'list':
        if (!arrayItemSchema) {
          throw new Error(`list item requires array item schema`);
        }
        schema = arrayItemSchema.array();
        break;
      case 'dict':
        if (!objectSchema) {
          throw new Error(`dict item requires object schema`);
        }
        schema = objectSchema;
        break;
      default:
        throw new Error(`unknown data type`);
    }
    return z.object({ [item.name]: schema });
  }, [item.name, item.data_type, arrayItemSchema, objectSchema]);

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const form = useForm({
    resolver: zodResolver(schema),
    disabled: disabled || transitioning,
    values: {
      [item.name]: item.value,
    },
    defaultValues: {
      [item.name]: item.default,
    },
  });

  // 判断是否是图片URL字段
  const isImageField = item.data_type === 'str' && 
    (item.name.includes('logo') || item.name.includes('image') || 
     item.name.includes('img') || item.name.includes('icon')) ||
    (typeof item.value === 'string' && IMAGE_URL_REGEX.test(item.value));

  // eslint-disable-next-line react-hooks/rules-of-hooks
  const Control = useCallback(({ field: { ...props } }: { field: ControllerRenderProps }) => {
    let el: ReactNode;

    if (children) {
      el = cloneElement(children(props), props);
    } else {
      switch (item.data_type) {
        case 'int':
          el = <Input type="number" step={1} placeholder={String(item.default)} {...props} />;
          break;
        case 'float':
          el = <Input type="number" {...props} placeholder={String(item.default)} />;
          break;
        case 'str':
          // 如果是图片URL字段，使用图片上传控件
          if (isImageField) {
            el = <ImageUploadInput {...props} />;
          } else {
          el = <Input {...props} placeholder={item.default} />;
          }
          break;
        case 'bool':
          el = <Switch className="block" {...props} onChange={undefined} checked={props.value} onCheckedChange={props.onChange} />;
          break;
        case 'dict':
        case 'list':
          throw new Error(`data type ${item.data_type} requires custom children`);
      }
    }

    return (
      <FormControl>
        {el}
      </FormControl>
    );
  }, [item.default, item.data_type, children, isImageField]);

  const handleSubmit = form.handleSubmit(async data => {
    try {
      await updateSiteSetting(name, data[item.name]);
      form.reset({ [item.name]: data[item.name] });
      startTransition(() => {
        router.refresh();
      });
      onChanged?.();
      toast.success(`设置已成功保存。`);
    } catch (error) {
      form.setError(item.name, { type: 'value', message: getErrorMessage(error) });
      setError(error instanceof Error ? error : new Error(String(error)));
      return Promise.reject(error);
    }
  });

  return (
    <Form {...form}>
      <form
        id={`setting_form_${name}`}
        className="space-y-2"
        onSubmit={handleSubmit}
        onReset={(e) => {
          form.setValue(item.name, item.default, { shouldTouch: true, shouldDirty: true });
          // void handleSubmit(e);
        }}
      >
        <FormField
          name={item.name}
          disabled={form.formState.isSubmitting}
          render={({ field }) => (
            <FormItem>
              <FormLabel>{displayName || capitalCase(item.name)}</FormLabel>
              <Control field={field} />
              <FormDescription>{item.description}</FormDescription>
              <FormMessage />
            </FormItem>
          )}
        />
        <Operations name={item.name} defaultValue={item.default} refreshing={transitioning} />
        {error && (
          <Alert variant="destructive" className="my-6">
            <AlertTitle>加载失败</AlertTitle>
            <AlertDescription>{getErrorMessage(error)}</AlertDescription>
          </Alert>
        )}
      </form>
    </Form>
  );
}

function Operations ({ refreshing, name, defaultValue }: { refreshing: boolean, name: string, defaultValue: any }) {
  const currentValue = useWatch({
    name,
  });
  const { isDirty, isSubmitting, disabled, isSubmitted } = useFormState();
  const notDefault = !deepEqual(currentValue, defaultValue);

  const deferredIsDirty = useDeferredValue(isDirty);
  const deferredIsSubmitting = useDeferredValue(isSubmitting);

  const successAndWaitRefreshing = !isSubmitting && (deferredIsSubmitting && refreshing);

  return (
    <div className="flex gap-2 items-center">
      {(isDirty || deferredIsDirty) && <Button className={cn('gap-2 items-center', successAndWaitRefreshing && 'bg-success')} type="submit" disabled={isSubmitting || successAndWaitRefreshing || disabled}>
        {(isSubmitting) && <Loader2Icon className="size-4 animate-spin repeat-infinite" />}
        {successAndWaitRefreshing && <CheckIcon className="size-4" />}
        {isSubmitting ? '保存中...' : refreshing ? '已保存' : '保存'}
      </Button>}
      {(isDirty || notDefault) && <Button type="reset" variant="secondary" disabled={isSubmitting || !notDefault || disabled}>重置</Button>}
    </div>
  );
}
