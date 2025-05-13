import { onSubmitHelper } from '@/components/form/utils';
import { Button } from '@/components/ui/button';
import { Form, FormControl, formDomEventHandlers, FormField } from '@/components/ui/form.beta';
import { Input } from '@/components/ui/input';
import { useDataTable } from '@/components/use-data-table';
import { useForm } from '@tanstack/react-form';
import { z } from 'zod';

export function KeywordFilterToolbar ({ onFilterChange, placeholder = "搜索评估数据集..." }: { onFilterChange: (filters: KeywordFilter) => void, placeholder?: string }) {
  const { loading } = useDataTable();

  const form = useForm({
    validators: {
      onSubmit: keywordFilter,
    },
    defaultValues: {
      keyword: '',
    },
    onSubmit: onSubmitHelper(keywordFilter, async ({ keyword, ...rest }) => {
      const trimmedKeyword = keyword?.trim();
      onFilterChange({
        keyword: trimmedKeyword ? trimmedKeyword : undefined,
        ...rest,
      });
    }, () => {}),
  });

  return (
    <Form form={form} disabled={loading}>
      <form className="flex gap-2 items-center" {...formDomEventHandlers(form)}>
        <FormField
          name="keyword"
          render={(field) => (
            <FormControl>
              <Input
                className="flex-1"
                placeholder={placeholder}
                name={field.name}
                onBlur={field.handleBlur}
                onChange={ev => field.handleChange(ev.target.value)}
                value={field.state.value ?? ''}
              />
            </FormControl>
          )}
        />
        <Button variant="secondary" disabled={loading} type="submit">
          搜索
        </Button>
      </form>
    </Form>
  );
}

const keywordFilter = z.object({
  keyword: z.string().optional(),
});

export type KeywordFilter = z.infer<typeof keywordFilter>;
