'use client';

import { ChangeEvent, ReactNode, useEffect, useId, useState, useTransition } from 'react';
import { z } from 'zod';
import { useForm } from '@tanstack/react-form';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { 
  DatabaseConnectionType, 
  DatabaseConnectionCreatePayload, 
  DatabaseConnectionUpdatePayload,
  createDatabaseConnection,
  updateDatabaseConnection,
  testDatabaseConfig,
  testSavedDatabaseConnection,
  ConnectionTestResponse
} from '@/api/database';

import { Form, formDomEventHandlers, FormSubmit, useFormContext } from '@/components/ui/form.beta';
import { FormRootError } from '@/components/form/root-error';
import { onSubmitHelper } from '@/components/form/utils';
import { FormInput, FormSwitch } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { FormSection, FormSectionsProvider, useFormSectionFields } from '@/components/form-sections';
import { SecondaryNavigatorItem, SecondaryNavigatorLayout, SecondaryNavigatorList, SecondaryNavigatorMain } from '@/components/secondary-navigator-list';
import { cn } from '@/lib/utils';
import { TestConnectionButton } from './TestConnectionButton';
import { DatabaseTypeSelect } from './DatabaseTypeSelect';

// 定义数据库连接配置类型
interface ConfigType {
  use_password?: boolean;
  password?: string;
  host?: string;
  port?: number;
  user?: string;
  database?: string;
  connection_string?: string;
  service_name?: string;
  sid?: string;
  [key: string]: any;
}

// 基础schema
const baseSchema = z.object({
  name: z.string().min(1, '请输入连接名称'),
  description: z.string().optional(),
  database_type: z.enum(['mysql', 'postgresql', 'mongodb', 'sql_server', 'oracle']),
  config: z.record(z.any()),
  read_only: z.boolean(),
  test_connection: z.boolean(),
});

// 验证schema
const nameSchema = z.string().min(1, '请输入连接名称');
const hostSchema = z.string().min(1, '请输入主机地址');
const portSchema = z.string().min(1, '请输入端口号');
const userSchema = z.string().min(1, '请输入用户名');
const databaseSchema = z.string().min(1, '请输入数据库名称');

type FormData = z.infer<typeof baseSchema>;
const field = formFieldLayout<FormData>();

interface DatabaseConnectionFormProps {
  mode: 'create' | 'update';
  existingConnection?: { 
    id: number;
    name: string;
    description: string;
    database_type: DatabaseConnectionType;
    config: ConfigType;
    read_only: boolean;
  };
  onSuccess?: (result: any) => void;
}

export function DatabaseConnectionForm({ mode, existingConnection, onSuccess }: DatabaseConnectionFormProps) {
  const id = useId();
  const [transitioning, startTransition] = useTransition();
  const [submissionError, setSubmissionError] = useState<unknown>();
  const router = useRouter();
  
  const [testConnectionResult, setTestConnectionResult] = useState<ConnectionTestResponse | null>(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [usePassword, setUsePassword] = useState(
    mode === 'update' ? existingConnection?.config?.use_password || false : false
  );

  // 获取数据库类型列表
  const [types, setTypes] = useState<Array<{ value: DatabaseConnectionType; label: string }>>([]);
  const [isLoadingTypes, setIsLoadingTypes] = useState<boolean>(true);
  const [typeError, setTypeError] = useState<string | null>(null);
  
  // 表单默认值
  const defaultValues = mode === 'update' && existingConnection
    ? {
        name: existingConnection.name,
        description: existingConnection.description || '',
        database_type: existingConnection.database_type,
        config: existingConnection.config,
        read_only: existingConnection.read_only,
        test_connection: false,
      }
    : {
        name: '',
        description: '',
        database_type: undefined as unknown as DatabaseConnectionType,
        config: {
          use_password: false
        } as ConfigType,
        read_only: true,
        test_connection: false,
      };
  
  // 表单实例
  const form = useForm<FormData>({
    defaultValues,
    onSubmit: mode === 'create'
      ? onSubmitHelper(baseSchema, async data => {
          try {
            // 验证字段
            validateFields(data);
            
            // 确保use_password字段存在
            if (data.config) {
              data.config.use_password = usePassword;
              
              // 如果不使用密码，确保密码字段为空
              if (!usePassword) {
                data.config.password = '';
              }
            }
            
            // 创建连接
            const newConnection = await createDatabaseConnection(data as DatabaseConnectionCreatePayload);
            toast.success(`数据库连接 ${newConnection.name} 创建成功`);
            
            // 调用成功回调或跳转
            if (onSuccess) {
              onSuccess(newConnection);
            } else {
              startTransition(() => {
                router.push(`/database-connections/${newConnection.id}`);
                router.refresh();
              });
            }
          } catch (err) {
            setSubmissionError(err);
            throw new Error(err instanceof Error ? err.message : '创建数据库连接失败');
          }
        }, setSubmissionError)
      : onSubmitHelper(baseSchema, async data => {
          try {
            if (!existingConnection) {
              throw new Error('找不到要更新的数据库连接');
            }
            
            // 构建更新payload
            const updatePayload: DatabaseConnectionUpdatePayload = {
              name: data.name,
              description: data.description,
              read_only: data.read_only,
              test_connection: false
            };
            
            // 确保use_password字段存在
            if (data.config) {
              data.config.use_password = usePassword;
              
              // 如果不使用密码，确保密码字段为空
              if (!usePassword) {
                data.config.password = '';
              }
              
              updatePayload.config = data.config;
            }
            
            // 更新连接
            const updatedConnection = await updateDatabaseConnection(existingConnection.id, updatePayload);
            toast.success('连接已更新');
            
            // 调用成功回调或跳转
            if (onSuccess) {
              onSuccess(updatedConnection);
            } else {
              startTransition(() => {
                router.refresh();
              });
            }
          } catch (err) {
            setSubmissionError(err);
            throw new Error(err instanceof Error ? err.message : '更新数据库连接失败');
          }
        }, setSubmissionError)
  });

  // 验证字段函数
  const validateFields = (data: FormData) => {
    // 根据数据库类型进行特定验证
    const config = data.config as ConfigType;
    
    switch (data.database_type) {
      case 'mysql':
      case 'postgresql':
      case 'sql_server':
        if (!config.host) throw new Error('请输入主机地址');
        if (!config.port) throw new Error('请输入端口');
        if (!config.user) throw new Error('请输入用户名');
        if (!config.database) throw new Error('请输入数据库名称');
        if (usePassword && !config.password) throw new Error('请输入密码');
        break;
      case 'mongodb':
        if (!config.connection_string) throw new Error('请输入连接字符串');
        break;
      case 'oracle':
        if (!config.host) throw new Error('请输入主机地址');
        if (!config.port) throw new Error('请输入端口');
        if (!config.user) throw new Error('请输入用户名');
        if (usePassword && !config.password) throw new Error('请输入密码');
        if (!config.service_name && !config.sid) 
          throw new Error('服务名称(Service Name)或SID至少填写一个');
        break;
    }
  };

  // 同步usePassword状态到form
  useEffect(() => {
    form.setFieldValue('config.use_password', usePassword);
  }, [usePassword, form]);

  // 处理测试连接
  const handleTestConnection = async () => {
    const databaseType = form.getFieldValue('database_type');
    if (!databaseType) {
      toast.error('请先选择数据库类型');
      return;
    }
    
    setIsTestingConnection(true);
    setTestConnectionResult(null);
    
    try {
      let result: ConnectionTestResponse;
      
      if (mode === 'update' && existingConnection) {
        // 测试已保存的连接
        result = await testSavedDatabaseConnection(existingConnection.id);
      } else {
        // 测试新配置
        const currentConfig = form.getFieldValue('config') as ConfigType || {};
        const payload = {
          name: form.getFieldValue('name') || '测试连接',
          description: form.getFieldValue('description') || '',
          database_type: databaseType,
          config: {
            ...currentConfig,
            use_password: usePassword
          } as ConfigType,
          read_only: form.getFieldValue('read_only') || true,
          test_connection: false
        };
        
        // 如果不使用密码，移除密码字段
        if (!usePassword && payload.config) {
          payload.config.password = '';
        }
        
        result = await testDatabaseConfig(payload);
      }
      
      setTestConnectionResult(result);
      if (result.success) {
        toast.success('连接测试成功');
      } else {
        toast.error(`连接测试失败: ${result.message}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : '测试连接失败';
      setTestConnectionResult({ success: false, message });
      toast.error(message);
    }
    
    setIsTestingConnection(false);
  };

  return (
    <Form form={form} disabled={transitioning} submissionError={submissionError}>
      <FormSectionsProvider>
        <form id={id} className="space-y-4" {...formDomEventHandlers(form, transitioning)}>
          <SecondaryNavigatorLayout defaultValue="基础信息">
            <SecondaryNavigatorList>
              <SectionTabTrigger required value="基础信息" />
              <SectionTabTrigger required value="连接信息" />
              <Separator />
              <FormRootError />
              <Button 
                className="w-full" 
                type="submit" 
                form={id} 
                disabled={form.state.isSubmitting || transitioning}
              >
                {mode === 'create' ? '创建连接' : '保存更改'}
              </Button>
              
              {form.getFieldValue('database_type') && (
                <Button
                  className="w-full mt-2" 
                  type="button"
                  variant="outline"
                  onClick={handleTestConnection}
                  disabled={isTestingConnection}
                >
                  测试连接
                </Button>
              )}
              
              {testConnectionResult && (
                <div className={`mt-2 text-sm ${testConnectionResult.success ? 'text-green-600' : 'text-red-600'}`}>
                  {testConnectionResult.message}
                </div>
              )}
            </SecondaryNavigatorList>

            {/* 基础信息 Section */}
            <Section title="基础信息">
              <field.Basic 
                name="name" 
                label="连接名称"
                validators={{ onSubmit: nameSchema, onBlur: nameSchema }}
              >
                <FormInput required />
              </field.Basic>

              <field.Basic name="description" label="描述 (可选)">
                <Textarea className="min-h-[80px]" />
              </field.Basic>

              <field.Basic 
                name="database_type" 
                label="数据库类型"
              >
                {mode === 'create' ? (
                  <DatabaseTypeSelect 
                    value={form.getFieldValue('database_type')}
                    onChange={(type) => {
                      form.setFieldValue('database_type', type);
                      
                      // 根据数据库类型设置默认端口
                      let defaultPort = 0;
                      if (type === 'mysql') defaultPort = 3306;
                      else if (type === 'postgresql') defaultPort = 5432;
                      else if (type === 'sql_server') defaultPort = 1433;
                      else if (type === 'oracle') defaultPort = 1521;
                      
                      form.setFieldValue('config', { 
                        use_password: usePassword,
                        port: defaultPort
                      } as ConfigType);
                      
                      setTestConnectionResult(null);
                    }}
                    disabled={transitioning}
                  />
                ) : (
                  <FormInput value={existingConnection?.database_type} disabled />
                )}
              </field.Basic>
            </Section>

            {/* 连接信息 Section */}
            <Section title="连接信息">
              {renderConnectionFields(form.getFieldValue('database_type'))}
              
              {/* 只读模式设置 */}
              <div className="space-y-2 mb-4">
                <div className="flex flex-row items-center justify-between py-4">
                  <div className="flex flex-col space-y-0.5">
                    <label className="text-sm font-medium">设置为只读模式</label>
                  </div>
                  <FormSwitch
                    id="readOnly"
                    value={form.getFieldValue('read_only')}
                    onChange={(value) => {
                      // 确保传入的是布尔值
                      const checked = typeof value === 'boolean' ? value : (value.target as HTMLInputElement).checked;
                      form.setFieldValue('read_only', checked);
                    }}
                  />
                </div>
              </div>
            </Section>
          </SecondaryNavigatorLayout>
        </form>
      </FormSectionsProvider>
    </Form>
  );
  
  // 渲染数据库连接配置字段
  function renderConnectionFields(databaseType?: DatabaseConnectionType) {
    if (!databaseType) return null;

    switch (databaseType) {
      case 'mysql':
      case 'postgresql':
      case 'sql_server':
        return (
          <>
            <SubSection title="连接设置">
              <field.Basic 
                name="config.host" 
                label="主机 (Host)"
                validators={{ onSubmit: hostSchema, onBlur: hostSchema }}
              >
                <FormInput required />
              </field.Basic>
              
              <field.Basic 
                name="config.port" 
                label="端口 (Port)"
                validators={{ onSubmit: portSchema, onBlur: portSchema }}
              >
                <FormInput type="number" required />
              </field.Basic>
              
              <field.Basic 
                name="config.user" 
                label="用户 (User)"
                validators={{ onSubmit: userSchema, onBlur: userSchema }}
              >
                <FormInput required />
              </field.Basic>
              
              <div className="space-y-2 mb-4">
                <div className="flex flex-row items-center justify-between py-4">
                  <div className="flex flex-col space-y-0.5">
                    <label className="text-sm font-medium">使用密码</label>
                  </div>
                  <FormSwitch
                    id="usePassword"
                    value={usePassword}
                    onChange={(value) => {
                      // 确保传入的是布尔值
                      const checked = typeof value === 'boolean' ? value : (value.target as HTMLInputElement).checked;
                      setUsePassword(checked);
                    }}
                  />
                </div>
              </div>
              
              {usePassword && (
                <field.Basic name="config.password" label="密码 (Password)">
                  <FormInput 
                    type="password" 
                    required={usePassword}
                    placeholder={mode === 'update' ? '●●●●' : undefined}
                  />
                </field.Basic>
              )}
              
              <field.Basic 
                name="config.database" 
                label="数据库名称 (Database)"
                validators={{ onSubmit: databaseSchema, onBlur: databaseSchema }}
              >
                <FormInput required />
              </field.Basic>
            </SubSection>
          </>
        );
        
      case 'mongodb':
        return (
          <SubSection title="连接设置">
            <field.Basic 
              name="config.connection_string" 
              label="连接字符串 (Connection String)"
            >
              <FormInput placeholder="mongodb://user:pass@host:port/db" required />
            </field.Basic>
          </SubSection>
        );
        
      case 'oracle':
        return (
          <>
            <SubSection title="连接设置">
              <field.Basic 
                name="config.host" 
                label="主机 (Host)"
                validators={{ onSubmit: hostSchema, onBlur: hostSchema }}
              >
                <FormInput required />
              </field.Basic>
              
              <field.Basic 
                name="config.port" 
                label="端口 (Port)"
                validators={{ onSubmit: portSchema, onBlur: portSchema }}
              >
                <FormInput type="number" defaultValue="1521" required />
              </field.Basic>
              
              <field.Basic 
                name="config.user" 
                label="用户 (User)"
                validators={{ onSubmit: userSchema, onBlur: userSchema }}
              >
                <FormInput required />
              </field.Basic>
              
              <div className="space-y-2 mb-4">
                <div className="flex flex-row items-center justify-between py-4">
                  <div className="flex flex-col space-y-0.5">
                    <label className="text-sm font-medium">使用密码</label>
                  </div>
                  <FormSwitch
                    id="usePassword"
                    value={usePassword}
                    onChange={(value) => {
                      // 确保传入的是布尔值
                      const checked = typeof value === 'boolean' ? value : (value.target as HTMLInputElement).checked;
                      setUsePassword(checked);
                    }}
                  />
                </div>
              </div>
              
              {usePassword && (
                <field.Basic name="config.password" label="密码 (Password)">
                  <FormInput 
                    type="password" 
                    required={usePassword}
                    placeholder={mode === 'update' ? '●●●●' : undefined}
                  />
                </field.Basic>
              )}
              
              <field.Basic name="config.service_name" label="服务名称 (Service Name)" description="例如 ORCLPDB1">
                <FormInput />
              </field.Basic>
              
              <field.Basic name="config.sid" label="SID" description="例如 ORCL">
                <FormInput />
              </field.Basic>
            </SubSection>
          </>
        );
        
      default:
        return <p className="text-sm text-gray-500">请先选择一种数据库类型以显示配置选项。</p>;
    }
  }
}

// Tab触发器组件
function SectionTabTrigger({ value, required }: { value: string, required?: boolean }) {
  const [invalid, setInvalid] = useState(false);
  const { form } = useFormContext();
  const fields = useFormSectionFields(value);

  useEffect(() => {
    return form.store.subscribe(() => {
      let invalid = false;
      for (let field of fields.values()) {
        if (field.getMeta().errors.length > 0) {
          invalid = true;
          break;
        }
      }
      setInvalid(invalid);
    });
  }, [form, fields, value]);

  return (
    <SecondaryNavigatorItem value={value}>
      <span className={cn(invalid && 'text-destructive')}>
        {value}
      </span>
      {required && <sup className="text-destructive" aria-hidden>*</sup>}
    </SecondaryNavigatorItem>
  );
}

// Section组件
function Section({ title, children }: { title: string, children: ReactNode }) {
  return (
    <FormSection value={title}>
      <SecondaryNavigatorMain className="space-y-8 max-w-screen-sm px-2 pb-8" value={title} strategy="hidden">
        {children}
      </SecondaryNavigatorMain>
    </FormSection>
  );
}

// SubSection组件
function SubSection({ title, children }: { title: ReactNode, children: ReactNode }) {
  return (
    <section className="space-y-4">
      <h4 className="text-lg">{title}</h4>
      {children}
    </section>
  );
} 