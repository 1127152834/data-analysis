'use client';

import { useId, useState, useEffect, useCallback } from 'react';
import { 
  DatabaseConnectionType, 
  DatabaseConnectionCreatePayload, 
  createDatabaseConnection, 
  testDatabaseConfig,
  ConnectionTestResponse,
  getDatabaseTypes,
  uploadSQLiteFile
} from '@/api/database';
import { DatabaseTypeSelect } from './DatabaseTypeSelect';
import { TestConnectionButton } from './TestConnectionButton';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { useForm } from '@tanstack/react-form';
import { Form, formDomEventHandlers, FormSubmit } from '@/components/ui/form.beta';
import { FormInput, FormSwitch } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { FormRootError } from '@/components/form/root-error';
import { onSubmitHelper } from '@/components/form/utils';
import { z } from 'zod';
import { toast } from 'sonner';
import { Switch } from '@/components/ui/switch';
import { FormCombobox } from '@/components/form/control-widget';
import { ChangeEvent, ReactNode } from 'react';
import { FormSection, FormSectionsProvider } from '@/components/form-sections';
import { SecondaryNavigatorItem, SecondaryNavigatorLayout, SecondaryNavigatorList, SecondaryNavigatorMain } from '@/components/secondary-navigator-list';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';

interface CreateDatabaseConnectionFormProps {
  onCreated: (newConnection: { id: number; name: string; database_type: DatabaseConnectionType }) => void;
  transitioning?: boolean;
}

// 基础schema
const baseSchema = z.object({
  name: z.string().min(1, '不能为空'),
  description: z.string().min(1, '不能为空'),
  database_type: z.enum(['mysql', 'postgresql', 'mongodb', 'sqlserver', 'oracle', 'sqlite'], {
    errorMap: () => ({ message: '不能为空' })
  }),
  config: z.record(z.any()),
  read_only: z.boolean(),
  test_connection: z.boolean(),
});

// MySQL/PostgreSQL/SQL Server的schema
const sqlSchema = baseSchema.extend({
  config: z.object({
    host: z.string().min(1, '不能为空'),
    port: z.number().min(1, '不能为空'),
    user: z.string().min(1, '不能为空'),
    database: z.string().min(1, '不能为空'),
    password: z.string().optional(),
    use_password: z.boolean().optional(),
  }).passthrough(),
});

// MongoDB的schema
const mongoSchema = baseSchema.extend({
  config: z.object({
    connection_string: z.string().min(1, '不能为空'),
    use_password: z.boolean().optional(),
  }).passthrough(),
});

// Oracle的schema
const oracleSchema = baseSchema.extend({
  config: z.object({
    host: z.string().min(1, '不能为空'),
    port: z.number().min(1, '不能为空'),
    user: z.string().min(1, '不能为空'),
    password: z.string().optional(),
    use_password: z.boolean().optional(),
  }).passthrough().refine(
    data => data.service_name || data.sid, 
    { message: '服务名称(Service Name)或SID至少填写一个' }
  ),
});

// SQLite的schema
const sqliteSchema = baseSchema.extend({
  config: z.object({
    file_path: z.string().min(1, '不能为空'),
  }).passthrough(),
});

// 定义更具体的配置类型
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
  file_path?: string;
  sqlite_file?: File;
  [key: string]: any;
}

type FormData = z.infer<typeof baseSchema>;
const field = formFieldLayout<FormData>();

export function CreateDatabaseConnectionForm({ onCreated, transitioning }: CreateDatabaseConnectionFormProps) {
  const id = useId();
  const [testConnectionResult, setTestConnectionResult] = useState<ConnectionTestResponse | null>(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [submissionError, setSubmissionError] = useState<unknown>();
  const [usePassword, setUsePassword] = useState(false);

  // 新增异步获取数据库类型
  const [types, setTypes] = useState<Array<{ value: DatabaseConnectionType; label: string }>>([]);
  const [isLoadingTypes, setIsLoadingTypes] = useState<boolean>(true);
  const [typeError, setTypeError] = useState<string | null>(null);
  
  // 获取数据库类型
  useEffect(() => {
    async function fetchTypes() {
      try {
        setIsLoadingTypes(true);
        setTypeError(null);
        const fetchedTypes = await getDatabaseTypes();
        setTypes(fetchedTypes);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : '获取数据库类型失败';
        console.error('获取数据库类型失败:', errorMessage);
        setTypeError(errorMessage);
        setTypes([]);
      }
      setIsLoadingTypes(false);
    }
    fetchTypes();
  }, []);

  const form = useForm<FormData>({
    defaultValues: {
      name: '',
      description: '',
      database_type: undefined as unknown as DatabaseConnectionType,
      config: {
        use_password: false
      } as ConfigType,
      read_only: true,
      test_connection: false,
    },
    onSubmit: onSubmitHelper(baseSchema, async (value) => {
      // 检查数据库类型是否已选择
      if (!value.database_type) {
        toast.error('请先选择数据库类型');
        throw new Error('请先选择数据库类型');
      }
      
      // 确保description有值 (对后端API来说这是必填的)
      if (!value.description) {
        value.description = value.name || '数据库连接';
      }
      
      // 确保use_password字段存在
      if (value.config) {
        value.config.use_password = usePassword;
        
        // 如果不使用密码，确保密码字段为空
        if (!usePassword) {
          value.config.password = '';
        }
        
        // 确保端口是数字类型
        if (typeof value.config.port === 'string') {
          value.config.port = parseInt(value.config.port, 10);
        }
        
        // 处理SQLite文件上传
        if (value.database_type === 'sqlite') {
          const sqliteFile = value.config.sqlite_file;
          if (!sqliteFile) {
            toast.error('请上传SQLite数据库文件');
            throw new Error('请上传SQLite数据库文件');
          }
          
          try {
            // 显示上传中提示
            const uploadToastId = toast.loading('正在上传SQLite数据库文件...');
            
            // 上传文件
            const uploadResult = await uploadSQLiteFile(sqliteFile);
            
            // 更新提示
            toast.success('SQLite数据库文件上传成功', {
              id: uploadToastId
            });
            
            // 将上传后的文件路径设置到配置中
            value.config.file_path = uploadResult.relative_path;
            
            // 移除文件对象，避免序列化问题
            delete value.config.sqlite_file;
          } catch (error) {
            toast.error('上传SQLite数据库文件失败: ' + (error instanceof Error ? error.message : String(error)));
            throw error;
          }
        }
      }
      
      // 根据数据库类型选择schema
      let schema;
      switch (value.database_type) {
        case 'mysql':
        case 'postgresql':
        case 'sqlserver':
          schema = sqlSchema;
          break;
        case 'mongodb':
          schema = mongoSchema;
          break;
        case 'oracle':
          schema = oracleSchema;
          break;
        case 'sqlite':
          schema = sqliteSchema;
          break;
        default:
          schema = baseSchema;
      }
      
      // 验证表单
      schema.parse(value);
      
      // 判断是否需要测试连接
      const shouldTestConnection = true; // 默认启用，也可以添加一个开关让用户选择

      // 如果需要测试连接
      if (shouldTestConnection) {
        // 显示测试连接中的提示
        const testToastId = toast.loading('正在测试连接...');
        
        try {
          // 准备测试连接的配置
          const testResult = await handleTestConnection();
          
          // 如果测试失败，中止创建过程
          if (!testResult.success) {
            toast.error('连接测试失败，无法创建连接', { id: testToastId });
            throw new Error(`连接测试失败: ${testResult.message}`);
          }
          
          // 测试成功，更新测试提示
          toast.success('连接测试成功', { id: testToastId });
          
          // 将test_connection参数设置为true
          value.test_connection = true;
        } catch (error) {
          // 处理测试过程中的错误
          toast.error('连接测试过程出错', { id: testToastId });
          throw error;
        }
      } else {
        // 不测试连接，将test_connection设为false
        value.test_connection = false;
      }
      
      // 创建连接
      console.log("提交数据:", value);
      const newConnection = await createDatabaseConnection(value as DatabaseConnectionCreatePayload);
      toast.success(`数据库连接 ${newConnection.name} 创建成功`);
      onCreated({ 
        id: newConnection.id, 
        name: newConnection.name, 
        database_type: newConnection.database_type 
      });
    }, setSubmissionError)
  });

  const [databaseTypeState, setDatabaseTypeState] = useState<DatabaseConnectionType | undefined>();
  const databaseType = form.getFieldValue('database_type') || databaseTypeState;

  // Define the callback with useCallback
  const handleDatabaseTypeChange = useCallback((type: DatabaseConnectionType) => {
    form.setFieldValue('database_type', type);
    setDatabaseTypeState(type);

    // 默认配置，确保所有可能的字段都有初始值
    let defaultConfig: ConfigType = {
      use_password: usePassword,
      host: '',     // 初始化为空字符串
      user: '',     // 初始化为空字符串
      database: '', // 初始化为空字符串
    };
    
    // 根据数据库类型设置端口
    if (type === 'mysql') defaultConfig.port = 3306;
    else if (type === 'postgresql') defaultConfig.port = 5432;
    else if (type === 'sqlserver') defaultConfig.port = 1433;
    else if (type === 'oracle') defaultConfig.port = 1521;
    else if (type === 'sqlite') {
      // SQLite 类型不需要这些字段，可以删除
      delete defaultConfig.host;
      delete defaultConfig.user;
      delete defaultConfig.port;
      // 但确保file_path有初始值
      defaultConfig.file_path = '';
    }

    form.setFieldValue('config', defaultConfig);
    // 确保read_only有默认值
    form.setFieldValue('read_only', true);
    setTestConnectionResult(null);
  }, [form, usePassword, setDatabaseTypeState]);

  // 同步usePassword状态到form
  useEffect(() => {
    form.setFieldValue('config.use_password', usePassword);
  }, [usePassword, form]);

  const handleTestConnection = async (): Promise<ConnectionTestResponse> => {
    if (!databaseType) {
      toast.error('请先选择数据库类型');
      return {
        success: false,
        message: '请先选择数据库类型'
      };
    }
    
    setIsTestingConnection(true);
    setTestConnectionResult(null);
    
    try {
      // 准备测试连接的配置
      const configValue = form.getFieldValue('config');
      const currentConfig = configValue ? { ...configValue } : {};
      
      const payload = {
        name: form.getFieldValue('name') || '测试连接',
        description: form.getFieldValue('description') || '测试连接',
        database_type: databaseType,
        config: {
          ...currentConfig,
          use_password: usePassword,
          port: typeof currentConfig.port === 'string' ? parseInt(currentConfig.port, 10) : currentConfig.port
        } as ConfigType,
        read_only: form.getFieldValue('read_only') || true,
        test_connection: false
      };
      
      // 如果不使用密码，移除密码字段
      if (!usePassword && payload.config) {
        payload.config.password = '';
      }
      
      console.log("测试连接配置:", payload);
      const result = await testDatabaseConfig(payload);
      
      // 设置新的测试结果
      setTestConnectionResult(result);
      
      if (result.success) {
        toast.success('连接测试成功');
      } else {
        toast.error(`连接测试失败: ${result.message}`);
      }
      return result;
    } catch (err) {
      const message = err instanceof Error ? err.message : '测试连接失败';
      const errorResult = { 
        success: false, 
        message 
      };
      setTestConnectionResult(errorResult);
      toast.error(message);
      return errorResult;
    } finally {
      setIsTestingConnection(false);
    }
  };

  return (
    <Form form={form} disabled={transitioning} submissionError={submissionError}>
      <FormSectionsProvider>
        <form id={id} className="space-y-4" {...formDomEventHandlers(form, transitioning)}>
          <SecondaryNavigatorLayout defaultValue="基础信息">
            <SecondaryNavigatorList>
              <SectionTabTrigger required value="基础信息" />
              <SectionTabTrigger required value="连接信息" />
              <SectionTabTrigger value="高级选项" />
              <Separator />
              <FormRootError title="创建数据库连接失败" />

              <Button 
                className="w-full" 
                type="submit" 
                form={id} 
                disabled={form.state.isSubmitting || transitioning}
              >
                创建连接
              </Button>
              
              {databaseType && (
                <div className="mt-4">
                  <TestConnectionButton 
                    onTest={handleTestConnection} 
                    disabled={isTestingConnection}
                    hideResult={false}
                  />
                </div>
              )}
            </SecondaryNavigatorList>

            <Section title="基础信息">
              <field.Basic 
                name="name" 
                label={<>连接名称 <span className="text-red-500">*</span></>}
                validators={{ 
                  onBlur: z.string().min(1, '不能为空'),
                  onChange: z.string().min(1, '不能为空')
                }}
              >
                <FormInput />
              </field.Basic>

              <field.Basic 
                name="description" 
                label={<>描述 <span className="text-red-500">*</span></>}
                validators={{ 
                  onBlur: z.string().min(1, '不能为空'),
                  onChange: z.string().min(1, '不能为空')
                }}
              >
                <Textarea placeholder="请输入数据库连接的描述信息" />
              </field.Basic>

              <SubSection title="数据库类型">
                <div className="space-y-2">
                  <label htmlFor="database_type" className="text-sm font-medium">数据库类型</label>
                  <DatabaseTypeSelect 
                    value={databaseType}
                    onChange={(type) => {
                      // 如果数据库类型改变，重置表单错误
                      if (databaseType !== type) {
                        setSubmissionError(undefined);
                      }
                      handleDatabaseTypeChange(type);
                    }}
                    disabled={isLoadingTypes || transitioning}
                  />
                  {!databaseType && form.state.isSubmitting && (
                    <p className="text-sm text-destructive">不能为空</p>
                  )}
                </div>
              </SubSection>
            </Section>

            <Section title="连接信息">
              {databaseType ? (
                <>
                  {(databaseType === 'mysql' || databaseType === 'postgresql' || databaseType === 'sqlserver') && (
                    <SubSection title="连接信息">
                      <field.Basic 
                        name="config.host" 
                        label="主机 (Host)"
                        validators={{ 
                          onBlur: z.string().min(1, '不能为空'),
                          onChange: z.string().min(1, '不能为空')
                        }}
                      >
                        <FormInput />
                      </field.Basic>
                      <field.Basic 
                        name="config.port" 
                        label="端口 (Port)"
                        validators={{
                          onBlur: z.coerce.number().min(1, '不能为空'),
                          onChange: z.coerce.number().min(1, '不能为空')
                        }}
                      >
                        <FormInput type="number" />
                      </field.Basic>
                      <field.Basic 
                        name="config.user" 
                        label="用户 (User)"
                        validators={{ 
                          onBlur: z.string().min(1, '不能为空'),
                          onChange: z.string().min(1, '不能为空')
                        }}
                      >
                        <FormInput />
                      </field.Basic>
                      
                      <div className="space-y-2 mb-4">
                        <div className="flex flex-row items-center justify-between py-4">
                          <div className="flex flex-col space-y-0.5">
                            <label className="text-sm font-medium">使用密码</label>
                          </div>
                          <Switch
                            id="usePassword"
                            checked={usePassword}
                            onCheckedChange={setUsePassword}
                          />
                        </div>
                      </div>
                      
                      {usePassword && (
                        <field.Basic 
                          name="config.password" 
                          label="密码 (Password)"
                          validators={{ 
                            onBlur: z.string().min(1, '不能为空'),
                            onChange: z.string().min(1, '不能为空')
                          }}
                        >
                          <FormInput type="password" />
                        </field.Basic>
                      )}
                      
                      <field.Basic 
                        name="config.database" 
                        label="数据库名称 (Database)"
                        validators={{ 
                          onBlur: z.string().min(1, '不能为空'),
                          onChange: z.string().min(1, '不能为空')
                        }}
                      >
                        <FormInput />
                      </field.Basic>
                    </SubSection>
                  )}
                  
                  {databaseType === 'mongodb' && (
                    <SubSection title="连接信息">
                      <field.Basic 
                        name="config.connection_string" 
                        label="连接字符串 (Connection String)"
                        validators={{ 
                          onBlur: z.string().min(1, '不能为空'),
                          onChange: z.string().min(1, '不能为空')
                        }}
                      >
                        <FormInput placeholder="mongodb://user:pass@host:port/db" />
                      </field.Basic>
                    </SubSection>
                  )}
                  
                  {databaseType === 'oracle' && (
                    <SubSection title="连接信息">
                      <field.Basic 
                        name="config.host" 
                        label="主机 (Host)"
                        validators={{ 
                          onBlur: z.string().min(1, '不能为空'),
                          onChange: z.string().min(1, '不能为空')
                        }}
                      >
                        <FormInput />
                      </field.Basic>
                      <field.Basic 
                        name="config.port" 
                        label="端口 (Port)"
                        validators={{
                          onBlur: z.coerce.number().min(1, '不能为空'),
                          onChange: z.coerce.number().min(1, '不能为空')
                        }}
                      >
                        <FormInput type="number" defaultValue={1521} aria-describedby="port-error" />
                      </field.Basic>
                      <field.Basic 
                        name="config.user" 
                        label="用户 (User)"
                        validators={{ 
                          onBlur: z.string().min(1, '不能为空'),
                          onChange: z.string().min(1, '不能为空')
                        }}
                      >
                        <FormInput />
                      </field.Basic>
                      
                      <div className="space-y-2 mb-4">
                        <div className="flex flex-row items-center justify-between py-4">
                          <div className="flex flex-col space-y-0.5">
                            <label className="text-sm font-medium">使用密码</label>
                          </div>
                          <Switch
                            id="usePassword"
                            checked={usePassword}
                            onCheckedChange={setUsePassword}
                          />
                        </div>
                      </div>
                      
                      {usePassword && (
                        <field.Basic 
                          name="config.password" 
                          label="密码 (Password)"
                          validators={{ 
                            onBlur: z.string().min(1, '不能为空'),
                            onChange: z.string().min(1, '不能为空')
                          }}
                        >
                          <FormInput type="password" />
                        </field.Basic>
                      )}
                      
                      <field.Basic name="config.service_name" label="服务名称 (Service Name)" description="例如 ORCLPDB1">
                        <FormInput />
                      </field.Basic>
                      
                      <field.Basic name="config.sid" label="SID" description="例如 ORCL">
                        <FormInput />
                      </field.Basic>
                    </SubSection>
                  )}

                  {databaseType === 'sqlite' && (
                    <SubSection title="连接信息">
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <label htmlFor="sqlite_file" className="text-sm font-medium">
                            数据库文件
                            <span className="text-red-500 ml-1">*</span>
                          </label>
                          <input
                            id="sqlite_file"
                            type="file"
                            accept=".db,.sqlite,.sqlite3"
                            className="w-full border border-gray-200 rounded-md p-2"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) {
                                form.setFieldValue('config.sqlite_file', file);
                              }
                            }}
                            disabled={form.state.isSubmitting || transitioning}
                          />
                          <p className="text-sm text-muted-foreground">
                            上传SQLite数据库文件，支持.db、.sqlite、.sqlite3格式
                          </p>
                        </div>
                        {form.getFieldValue('config.sqlite_file') && (
                          <p className="text-sm">
                            已选择文件: {form.getFieldValue('config.sqlite_file').name}
                          </p>
                        )}
                      </div>
                    </SubSection>
                  )}
                </>
              ) : (
                <p className="text-sm text-gray-500">请先在基础信息中选择一种数据库类型</p>
              )}
            </Section>

            <Section title="高级选项">
              <SubSection title="访问模式">
                <div className="space-y-2 mb-4">
                  <div className="flex flex-row items-center justify-between py-4">
                    <div className="flex flex-col space-y-0.5">
                      <label className="text-sm font-medium">设置为只读模式</label>
                      <p className="text-sm text-muted-foreground">限制对数据库的写入操作，仅允许查询</p>
                    </div>
                    <Switch
                      id="readOnly"
                      checked={form.getFieldValue('read_only')}
                      onCheckedChange={(checked) => {
                        form.setFieldValue('read_only', Boolean(checked));
                      }}
                    />
                  </div>
                </div>
                
                <div className="space-y-2 mb-4">
                  <div className="flex flex-row items-center justify-between py-4">
                    <div className="flex flex-col space-y-0.5">
                      <label className="text-sm font-medium">创建前测试连接</label>
                      <p className="text-sm text-muted-foreground">在创建连接前验证连接是否可用</p>
                    </div>
                    <Switch
                      id="testConnection"
                      checked={form.getFieldValue('test_connection') !== false}
                      onCheckedChange={(checked) => {
                        form.setFieldValue('test_connection', Boolean(checked));
                      }}
                    />
                  </div>
                </div>
              </SubSection>
            </Section>
          </SecondaryNavigatorLayout>
        </form>
      </FormSectionsProvider>
    </Form>
  );
}

// Tab触发器组件
function SectionTabTrigger({ value, required }: { value: string, required?: boolean }) {
  return (
    <SecondaryNavigatorItem value={value}>
      <span>
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
 
 