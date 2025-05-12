'use client';

// 数据库类型选择组件
import { useEffect, useState } from 'react';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { DatabaseConnectionType, getDatabaseTypes } from '@/api/database';

interface DatabaseTypeSelectProps {
  value?: DatabaseConnectionType;
  onChange: (value: DatabaseConnectionType) => void;
  disabled?: boolean;
}

export function DatabaseTypeSelect({ value, onChange, disabled }: DatabaseTypeSelectProps) {
  const [types, setTypes] = useState<Array<{ value: DatabaseConnectionType; label: string }>>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // 加载数据库类型
  useEffect(() => {
    const loadDatabaseTypes = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        // 注意：如果后端API不存在，可以使用以下静态数据
        const staticTypes = [
          { value: 'mysql' as DatabaseConnectionType, label: 'MySQL' },
          { value: 'postgresql' as DatabaseConnectionType, label: 'PostgreSQL' },
          { value: 'mongodb' as DatabaseConnectionType, label: 'MongoDB' },
          { value: 'sql_server' as DatabaseConnectionType, label: 'SQL Server' },
          { value: 'oracle' as DatabaseConnectionType, label: 'Oracle' },
        ];
        
        try {
          // 尝试从API获取
          const typesList = await getDatabaseTypes();
          setTypes(typesList);
        } catch (e) {
          // 如果API失败，使用静态数据
          console.warn('Failed to fetch database types from API, using static data', e);
          setTypes(staticTypes);
        }
      } catch (err) {
        setError('获取数据库类型列表失败');
        console.error('Failed to load database types:', err);
      } finally {
        setIsLoading(false);
      }
    };

    loadDatabaseTypes();
  }, []);

  return (
    <Select 
      value={value}
      onValueChange={value => onChange(value as DatabaseConnectionType)}
      disabled={disabled || isLoading}
    >
      <SelectTrigger>
        <SelectValue placeholder="选择数据库类型" />
      </SelectTrigger>
      <SelectContent>
        {error ? (
          <SelectItem value="_error" disabled>
            {error}
          </SelectItem>
        ) : isLoading ? (
          <SelectItem value="_loading" disabled>
            加载中...
          </SelectItem>
        ) : (
          types.map((type) => (
            <SelectItem key={type.value} value={type.value}>
              {type.label}
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  );
} 