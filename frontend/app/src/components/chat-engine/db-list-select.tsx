import { type FormControlWidgetProps } from '@/components/form/control-widget';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent } from '@/components/ui/popover';
import { getErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import * as PopoverPrimitive from '@radix-ui/react-popover';
import { AlertTriangleIcon, CheckIcon, DotIcon, DatabaseIcon } from 'lucide-react';
import * as React from 'react';
import { useState } from 'react';
import { getDatabaseConnections } from '@/api/database';
import { type DatabaseConnection } from '@/api/database';

// 使用简单的自定义hooks替代react-query
function useDatabaseConnections() {
  const [data, setData] = useState<DatabaseConnection[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  React.useEffect(() => {
    async function fetchData() {
      try {
        setIsLoading(true);
        const connections = await getDatabaseConnections();
        setData(Array.isArray(connections) ? connections : connections.items);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setIsLoading(false);
      }
    }
    
    fetchData();
  }, []);

  return { data, isLoading, error };
}

export function DBListSelect ({ ref, disabled, value, onChange, ...props }: FormControlWidgetProps<number[]>) {
  const [open, setOpen] = useState(false);
  const { data: databaseConnections, isLoading, error } = useDatabaseConnections();
  
  const isConfigReady = !isLoading && !error;

  const current = value?.map(id => {
    if (!databaseConnections) return null;
    return databaseConnections.find((db: DatabaseConnection) => db.id === id);
  });

  const connections = databaseConnections || [];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <div className={cn('flex items-center gap-2')}>
        <PopoverPrimitive.Trigger
          ref={ref}
          disabled={disabled || !isConfigReady}
          className={cn(
            'flex flex-col min-h-10 w-full text-left items-stretch justify-start rounded-md border border-input bg-background px-3 py-1 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
          )}
          {...props}
        >
          {isLoading
            ? <span>正在加载选项...</span>
            : !!error
              ? <span className="text-destructive">{getErrorMessage(error)}</span>
              : !!current?.length
                ? current.map((option, index) => (
                  option ? (
                    <div key={option.id} className="w-full block border-t first-of-type:border-t-0 py-2">
                      <span>{option.name}</span>
                      <div className="text-xs text-muted-foreground ml-2 inline-flex gap-1 items-center">
                        <DatabaseIcon className="size-3" />
                        <span>{option.database_type}</span>
                        <DotIcon className="size-4" />
                        <span className={cn("text-xs", 
                          option.connection_status === 'connected' ? "text-green-500" : 
                          option.connection_status === 'error' ? "text-destructive" : 
                          "text-muted-foreground"
                        )}>
                          {option.connection_status === 'connected' ? '已连接' : 
                           option.connection_status === 'error' ? '连接错误' : '未连接'}
                        </span>
                      </div>
                    </div>
                  ) : <span key={value?.[index]}>未知数据库 {value?.[index]}</span>
                )) 
                : <span className="pt-1 text-muted-foreground">选择数据库源</span>
          }
        </PopoverPrimitive.Trigger>
      </div>
      <PopoverContent className={cn('p-0 focus:outline-none w-[--radix-popover-trigger-width]')} align="start" collisionPadding={8}>
        <Command>
          <CommandInput placeholder="搜索数据库..." />
          <CommandList>
            <CommandGroup>
              {connections.map((option: DatabaseConnection) => (
                <CommandItem
                  key={option.id}
                  value={String(option.id)}
                  keywords={[option.name, option.description || '', option.database_type]}
                  className={cn('group')}
                  onSelect={idValue => {
                    const id = connections.find((opt: DatabaseConnection) => String(opt.id) === idValue)?.id;
                    if (id) {
                      if (value?.includes(id)) {
                        onChange?.(value.filter(v => v !== id));
                      } else {
                        onChange?.([...(value ?? []), id]);
                      }
                    }
                  }}
                >
                  <div className="space-y-1">
                    <div className="flex items-center">
                      <DatabaseIcon className="mr-2 size-4" />
                      <strong>
                        {option.name}
                      </strong>
                    </div>
                    <div className="text-xs text-muted-foreground flex gap-1 items-center">
                      <span>{option.database_type}</span>
                      <DotIcon className="size-4" />
                      <span className={cn(
                        option.connection_status === 'connected' ? "text-green-500" : 
                        option.connection_status === 'error' ? "text-destructive" : 
                        "text-muted-foreground"
                      )}>
                        {option.connection_status === 'connected' ? '已连接' : 
                         option.connection_status === 'error' ? '连接错误' : '未连接'}
                      </span>
                    </div>
                    {option.description && (
                      <div className="text-xs text-muted-foreground">
                        {option.description}
                      </div>
                    )}
                  </div>
                  <CheckIcon className={cn('ml-auto size-4 opacity-0 flex-shrink-0', value?.includes(option.id) && 'opacity-100')} />
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandEmpty className="text-muted-foreground/50 text-xs p-4 text-center">
              未找到数据库源
            </CommandEmpty>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export function DBListSelectForObjectValue ({ value, onChange, ...props }: FormControlWidgetProps<{ id: number }[], true>) {
  return (
    <DBListSelect
      value={value?.map(v => v.id) ?? []}
      onChange={value => {
        onChange?.((value as number[]).map(id => ({ id })));
      }}
      {...props}
    />
  );
} 