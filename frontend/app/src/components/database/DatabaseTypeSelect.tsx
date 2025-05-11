// 数据库类型选择组件
import { useState, useEffect, ChangeEvent } from 'react';
import { DatabaseConnectionType, getDatabaseTypes } from '@/api/database';
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { FormCombobox } from '@/components/form/control-widget';
import { Loader2Icon } from 'lucide-react';

interface DatabaseTypeSelectProps {
  value?: DatabaseConnectionType;
  onChange: (value: DatabaseConnectionType) => void;
  disabled?: boolean; // Optional: to disable the select
}

export function DatabaseTypeSelect({ value, onChange, disabled }: DatabaseTypeSelectProps) {
  const [types, setTypes] = useState<Array<{ value: DatabaseConnectionType; label: string }>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchTypes() {
      try {
        setIsLoading(true);
        setError(null);
        const fetchedTypes = await getDatabaseTypes();
        setTypes(fetchedTypes);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
        console.error('Failed to fetch database types:', errorMessage);
        setError(errorMessage);
        setTypes([]); // Clear types on error
      }
      setIsLoading(false);
    }
    fetchTypes();
  }, []);

  // 转换数据到FormCombobox需要的格式
  const options = types.map(type => ({
    id: type.value,
    name: type.label,
    provider: 'database',
    model: type.value,
  }));

  // 处理FormCombobox的onChange事件
  const handleChange = (newValue: string | ChangeEvent<any> | undefined) => {
    if (typeof newValue === 'string' && newValue) {
      onChange(newValue as DatabaseConnectionType);
    }
  };

  return (
    <FormCombobox
      placeholder="选择数据库类型"
      value={value}
      onChange={handleChange}
      disabled={disabled}
      config={{
        options,
        loading: isLoading,
        error,
        optionKeywords: (option) => [option.name, option.model],
        renderValue: (option) => (
          <span>{option.name}</span>
        ),
        renderOption: (option) => (
          <div>
            <div className="font-medium">{option.name}</div>
          </div>
        ),
        key: 'id',
      }}
    />
  );
} 