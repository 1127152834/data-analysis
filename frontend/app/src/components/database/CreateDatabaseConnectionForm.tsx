'use client';

import { ChangeEvent, FormEvent, useState } from 'react';
import { 
  DatabaseConnectionType, 
  DatabaseConnectionCreatePayload, 
  createDatabaseConnection, 
  testDatabaseConnection,
  ConnectionTestResponse
} from '@/api/database';
import { DatabaseTypeSelect } from './DatabaseTypeSelect';
import { TestConnectionButton } from './TestConnectionButton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';

interface CreateDatabaseConnectionFormProps {
  onCreated: (newConnection: { id: number; name: string; database_type: DatabaseConnectionType }) => void;
  transitioning?: boolean;
}

export function CreateDatabaseConnectionForm({ onCreated, transitioning }: CreateDatabaseConnectionFormProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [databaseType, setDatabaseType] = useState<DatabaseConnectionType | undefined>(undefined);
  const [config, setConfig] = useState<Record<string, any>>({});
  const [readOnly, setReadOnly] = useState(true);
  
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testConnectionResult, setTestConnectionResult] = useState<ConnectionTestResponse | null>(null);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfigChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name: fieldName, value, type } = e.target;
    // @ts-ignore - Consider a more type-safe way to handle checkbox if time permits
    const fieldValue = type === 'checkbox' ? (e.target as HTMLInputElement).checked : type === 'number' ? parseInt(value, 10) : value;
    setConfig(prev => ({ ...prev, [fieldName]: fieldValue }));
  };

  const handleTestConnection = async () => {
    if (!databaseType) {
      alert('请先选择数据库类型');
      return;
    }
    setIsTestingConnection(true);
    setTestConnectionResult(null);
    setError(null);
    try {
      const payload: DatabaseConnectionCreatePayload = { 
        name: name || '测试连接',
        description: description || '',
        database_type: databaseType, 
        config, 
        read_only: readOnly,
        test_connection: false
      };
      const result = await testDatabaseConnection(payload);
      setTestConnectionResult(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : '测试连接失败';
      setTestConnectionResult({ success: false, message });
    }
    setIsTestingConnection(false);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!databaseType) {
      setError('请选择数据库类型');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setTestConnectionResult(null);

    const payload: DatabaseConnectionCreatePayload = {
      name,
      description,
      database_type: databaseType,
      config,
      read_only: readOnly,
      test_connection: false,
    };

    try {
      const newConnection = await createDatabaseConnection(payload);
      onCreated({ id: newConnection.id, name: newConnection.name, database_type: newConnection.database_type }); 
    } catch (err) {
      const message = err instanceof Error ? err.message : '创建数据库连接失败';
      setError(message);
      console.error(err);
    }
    setIsSubmitting(false);
  };

  const renderConfigFields = () => {
    if (!databaseType) return null;

    switch (databaseType) {
      case 'mysql':
      case 'postgresql':
      case 'sql_server':
        return (
          <>
            <div className="mb-4">
              <Label htmlFor="host">主机 (Host)</Label>
              <Input id="host" name="host" value={config.host || ''} onChange={handleConfigChange} required />
            </div>
            <div className="mb-4">
              <Label htmlFor="port">端口 (Port)</Label>
              <Input id="port" name="port" type="number" value={config.port || ''} onChange={handleConfigChange} required />
            </div>
            <div className="mb-4">
              <Label htmlFor="user">用户 (User)</Label>
              <Input id="user" name="user" value={config.user || ''} onChange={handleConfigChange} required />
            </div>
            <div className="mb-4">
              <Label htmlFor="password">密码 (Password)</Label>
              <Input id="password" name="password" type="password" value={config.password || ''} onChange={handleConfigChange} />
            </div>
            <div className="mb-4">
              <Label htmlFor="database">数据库名称 (Database)</Label>
              <Input id="database" name="database" value={config.database || ''} onChange={handleConfigChange} required />
            </div>
          </>
        );
      case 'mongodb':
        return (
          <div className="mb-4">
            <Label htmlFor="connection_string">连接字符串 (Connection String)</Label>
            <Input id="connection_string" name="connection_string" value={config.connection_string || ''} onChange={handleConfigChange} placeholder="mongodb://user:pass@host:port/db" required />
          </div>
        );
      case 'oracle':
         return (
          <>
            <div className="mb-4">
              <Label htmlFor="host">主机 (Host)</Label>
              <Input id="host" name="host" value={config.host || ''} onChange={handleConfigChange} required />
            </div>
            <div className="mb-4">
              <Label htmlFor="port">端口 (Port)</Label>
              <Input id="port" name="port" type="number" value={config.port || 1521} onChange={handleConfigChange} required />
            </div>
            <div className="mb-4">
              <Label htmlFor="user">用户 (User)</Label>
              <Input id="user" name="user" value={config.user || ''} onChange={handleConfigChange} required />
            </div>
            <div className="mb-4">
              <Label htmlFor="password">密码 (Password)</Label>
              <Input id="password" name="password" type="password" value={config.password || ''} onChange={handleConfigChange} />
            </div>
            <div className="mb-4">
              <Label htmlFor="service_name">服务名称 (Service Name)</Label>
              <Input id="service_name" name="service_name" value={config.service_name || ''} onChange={handleConfigChange} placeholder="例如 ORCLPDB1" />
              <p className="text-xs text-gray-500 mt-1">或者填写 SID。</p>
               <Label htmlFor="sid" className="mt-2">SID</Label>
              <Input id="sid" name="sid" value={config.sid || ''} onChange={handleConfigChange} placeholder="例如 ORCL" />
            </div>
          </>
        );
      default:
        return <p className="text-sm text-gray-500">请先选择一种数据库类型以显示配置选项。</p>;
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="mb-4">
        <Label htmlFor="name">连接名称</Label>
        <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required />
      </div>

      <div className="mb-4">
        <Label htmlFor="description">描述 (可选)</Label>
        <Textarea id="description" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>

      <div className="mb-4">
        <Label htmlFor="databaseType">数据库类型</Label>
        <DatabaseTypeSelect 
          value={databaseType}
          onChange={(type) => {
            setDatabaseType(type);
            setConfig({}); 
            setTestConnectionResult(null);
          }}
        />
      </div>

      {renderConfigFields()}

      <div className="mb-4 flex items-center space-x-2">
        <Checkbox id="readOnly" checked={readOnly} onCheckedChange={(checked) => setReadOnly(Boolean(checked))} />
        <Label htmlFor="readOnly">设置为只读模式</Label>
      </div>
      
      {databaseType && (
        <div className="my-4">
          <TestConnectionButton onClick={handleTestConnection} loading={isTestingConnection} />
          {testConnectionResult && (
            <p className={`mt-2 text-sm ${testConnectionResult.success ? 'text-green-600' : 'text-red-600'}`}>
              {testConnectionResult.message}
            </p>
          )}
        </div>
      )}

      {error && <p className="text-red-500">错误: {error}</p>}

      <Button type="submit" disabled={isSubmitting || transitioning || !databaseType }>
        {isSubmitting ? '正在创建...' : '创建连接'}
      </Button>
    </form>
  );
} 
 