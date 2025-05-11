'use client';

import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import {
  DatabaseConnection,
  DatabaseConnectionType,
  DatabaseConnectionUpdatePayload,
  updateDatabaseConnection,
  testSavedDatabaseConnection,
  ConnectionTestResponse
} from '@/api/database';
import { DatabaseTypeSelect } from './DatabaseTypeSelect';
import { TestConnectionButton } from './TestConnectionButton';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { FormCheckbox } from '@/components/form/control-widget';
import { toast } from 'sonner';
import { Card, CardContent } from '@/components/ui/card';
import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface UpdateDatabaseConnectionFormProps {
  connection: DatabaseConnection;
  onUpdated: (updatedConnection: DatabaseConnection) => void;
  transitioning?: boolean;
}

export function UpdateDatabaseConnectionForm({ connection, onUpdated, transitioning }: UpdateDatabaseConnectionFormProps) {
  const [name, setName] = useState(connection.name);
  const [description, setDescription] = useState(connection.description);
  const [databaseType, setDatabaseType] = useState<DatabaseConnectionType | undefined>(connection.database_type);
  const [config, setConfig] = useState<Record<string, any>>({});
  const [readOnly, setReadOnly] = useState(connection.read_only);

  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [testConnectionResult, setTestConnectionResult] = useState<ConnectionTestResponse | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setName(connection.name);
    setDescription(connection.description);
    setDatabaseType(connection.database_type);
    
    const initialConfig = { ...(connection.config || {}) };
    delete initialConfig.password;
    setConfig(initialConfig);
    
    setReadOnly(connection.read_only);
    setError(null);
    setTestConnectionResult(null);
  }, [connection]);

  const handleConfigChange = (e: ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name: fieldName, value, type } = e.target;
    const target = e.target as HTMLInputElement;
    const fieldValue = type === 'checkbox' ? target.checked : type === 'number' ? parseInt(value, 10) : value;
    setConfig(prev => ({ ...prev, [fieldName]: fieldValue }));
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setTestConnectionResult(null);
    setError(null);
    
    const loadingToast = toast.loading(`正在测试连接 "${name}"...`);
    
    try {
      const result = await testSavedDatabaseConnection(connection.id);
      setTestConnectionResult(result);
      
      toast.dismiss(loadingToast);
      
      if (result.success) {
        toast.success('连接测试成功', {
          description: result.message || '数据库连接测试成功',
        });
      } else {
        toast.error('连接测试失败', {
          description: result.message || '无法连接到数据库',
        });
      }
    } catch (err: any) {
      toast.dismiss(loadingToast);
      
      const errorMessage = err instanceof Error ? err.message : '测试连接时发生错误';
      toast.error('连接测试失败', {
        description: errorMessage,
      });
      setTestConnectionResult({
        success: false,
        message: errorMessage
      });
    }
    
    setIsTestingConnection(false);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!databaseType) {
      setError('数据库类型不能为空');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setTestConnectionResult(null);

    const payloadConfig = { ...config };
    if (config.password === '') {
      delete payloadConfig.password;
    }

    const payload: DatabaseConnectionUpdatePayload = {
      name,
      description,
      database_type: databaseType,
      config: payloadConfig,
      read_only: readOnly,
      test_connection: false,
    };

    try {
      const updatedConnection = await updateDatabaseConnection(connection.id, payload);
      onUpdated(updatedConnection);
    } catch (err) {
      const message = err instanceof Error ? err.message : '更新数据库连接失败';
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
              <Input id="password" name="password" type="password" value={config.password || ''} onChange={handleConfigChange} placeholder="如需修改请输入新密码" />
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
              <Input id="password" name="password" type="password" value={config.password || ''} onChange={handleConfigChange} placeholder="如需修改请输入新密码"/>
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
      <Card className="shadow-sm">
        <CardContent className="pt-6">
          <div className="mb-6">
            <Label htmlFor="name" className="mb-2 block">连接名称</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} required className="w-full" />
          </div>

          <div className="mb-6">
            <Label htmlFor="description" className="mb-2 block">描述 (可选)</Label>
            <Textarea 
              id="description" 
              value={description} 
              onChange={(e) => setDescription(e.target.value)} 
              className="w-full min-h-[80px]"
            />
          </div>

          <div className="mb-6">
            <Label htmlFor="databaseType" className="mb-2 block">数据库类型</Label>
            <DatabaseTypeSelect 
              value={databaseType}
              onChange={(type) => {
                setDatabaseType(type);
                setTestConnectionResult(null);
              }}
            />
          </div>

          {renderConfigFields()}

          <div className="mb-6 flex items-center space-x-2">
            <FormCheckbox 
              id="readOnly" 
              value={readOnly} 
              onChange={(checked) => {
                if (typeof checked === 'boolean') {
                  setReadOnly(checked);
                }
              }}
            />
            <Label htmlFor="readOnly" className="cursor-pointer">设置为只读模式</Label>
          </div>
          
          {databaseType && (
            <div className="my-6">
              <TestConnectionButton 
                onClick={handleTestConnection} 
                loading={isTestingConnection} 
                success={testConnectionResult?.success}
              />
              {testConnectionResult && !testConnectionResult.success && (
                <Alert variant="destructive" className="mt-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>连接失败</AlertTitle>
                  <AlertDescription className="mt-2">
                    {testConnectionResult.message}
                    {testConnectionResult.details && (
                      <pre className="mt-2 text-xs bg-background/80 p-2 rounded-md whitespace-pre-wrap overflow-x-auto">
                        {JSON.stringify(testConnectionResult.details, null, 2)}
                      </pre>
                    )}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}

          {error && (
            <Alert variant="destructive" className="mt-4 mb-6">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>保存失败</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button 
            type="submit" 
            disabled={isSubmitting || transitioning || !databaseType}
            className="w-full md:w-auto"
          >
            {isSubmitting ? '正在保存...' : '保存更改'}
          </Button>
        </CardContent>
      </Card>
    </form>
  );
} 