'use client';

import { ChangeEvent, FormEvent, useEffect, useState, ReactNode } from 'react';
import {
  DatabaseConnection,
  DatabaseConnectionType,
  DatabaseConnectionUpdatePayload,
  updateDatabaseConnection,
  testSavedDatabaseConnection,
  testDatabaseConfig,
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
import { fieldAccessor, GeneralSettingsField, type GeneralSettingsFieldAccessor, GeneralSettingsForm } from '@/components/settings-form';
import { FormInput, FormSwitch } from '@/components/form/control-widget';
import { formFieldLayout } from '@/components/form/field-layout';
import { useRouter } from 'next/navigation';
import { useTransition } from 'react';
import { z } from 'zod';
import { FormSection, FormSectionsProvider } from '@/components/form-sections';
import { SecondaryNavigatorItem, SecondaryNavigatorLayout, SecondaryNavigatorList, SecondaryNavigatorMain } from '@/components/secondary-navigator-list';
import { Separator } from '@/components/ui/separator';

interface UpdateDatabaseConnectionFormProps {
  connection: DatabaseConnection;
  onUpdated: (updatedConnection: DatabaseConnection) => void;
  transitioning?: boolean;
}

export function UpdateDatabaseConnectionForm({ connection, onUpdated, transitioning: externalTransitioning }: UpdateDatabaseConnectionFormProps) {
  const [internalTransitioning, startTransition] = useTransition();
  const transitioning = externalTransitioning || internalTransitioning;
  const router = useRouter();
  const [usePassword, setUsePassword] = useState(connection.config && (connection.config.use_password || false));
  const [testConnectionResult, setTestConnectionResult] = useState<ConnectionTestResponse | null>(null);

  // 定义schema
  const nameSchema = z.string().min(1, "名称不能为空");
  const descriptionSchema = z.string().optional();
  const readOnlySchema = z.boolean();
  
  // 创建字段访问器
  const nameAccessor = fieldAccessor<DatabaseConnectionUpdatePayload, 'name'>('name');
  const descriptionAccessor = fieldAccessor<DatabaseConnectionUpdatePayload, 'description'>('description');
  const readOnlyAccessor = fieldAccessor<DatabaseConnectionUpdatePayload, 'read_only'>('read_only');
  
  // 创建host, port, user, database字段访问器
  const configAccessor = (key: string): GeneralSettingsFieldAccessor<DatabaseConnectionUpdatePayload, string> => {
    return {
      path: ['config', key],
      get(data) {
        return data.config?.[key] || '';
      },
      set(data, value) {
        const newConfig = { ...(data.config || {}) };
        newConfig[key] = value;
        return {
          ...data,
          config: newConfig
        };
      }
    };
  };
  
  // 创建usePassword字段访问器
  const usePasswordAccessor: GeneralSettingsFieldAccessor<DatabaseConnectionUpdatePayload, boolean> = {
    path: ['config', 'use_password'],
    get(data) {
      if ('use_password' in (data.config || {})) {
        return !!data.config?.use_password;
      }
      return 'password' in (data.config || {}) || 'password_encrypted' in (data.config || {});
    },
    set(data, value) {
      const newConfig = { ...(data.config || {}) };
      newConfig.use_password = value;
      // 如果不使用密码，删除密码字段
      if (!value) {
        delete newConfig.password;
      }
      return {
        ...data,
        config: newConfig
      };
    }
  };
  
  // 密码字段访问器
  const passwordAccessor: GeneralSettingsFieldAccessor<DatabaseConnectionUpdatePayload, string> = {
    path: ['config', 'password'],
    get(data) {
      return data.config?.password || '';
    },
    set(data, value) {
      const newConfig = { ...(data.config || {}) };
      newConfig.password = value;
      return {
        ...data,
        config: newConfig
      };
    }
  };

  // 处理字段更新
  const handleUpdate = async (data: Partial<DatabaseConnectionUpdatePayload>, path: string[]) => {
    // 特殊处理usePassword
    if (path[0] === 'config' && path[1] === 'use_password') {
      setUsePassword(!!data.config?.use_password);
    }
    
    try {
      // 构建更新payload
      const updatePayload: DatabaseConnectionUpdatePayload = {
        test_connection: false
      };
      
      // 根据路径构建更新数据
      if (path[0] === 'config') {
        updatePayload.config = data.config;
      } else {
        // @ts-ignore
        updatePayload[path[0]] = data[path[0]];
      }
      
      // 发送更新请求
      const updatedConnection = await updateDatabaseConnection(connection.id, updatePayload);
      
      toast.success('连接已更新');
      onUpdated(updatedConnection);
      
      // 刷新页面
      startTransition(() => {
        router.refresh();
      });
    } catch (err) {
      // 直接使用错误信息
      toast.error(err instanceof Error ? err.message : '更新数据库连接失败');
    }
  };

  const handleTestConnection = async (): Promise<ConnectionTestResponse> => {
    try {
      const result = await testSavedDatabaseConnection(connection.id);
      setTestConnectionResult(result);
      
      if (result.success) {
        toast.success('连接测试成功', {
          description: result.message || '数据库连接测试成功',
        });
      } else {
        toast.error('连接测试失败', {
          description: result.message || '无法连接到数据库',
        });
      }
      
      return result;
    } catch (err: any) {
      const errorMessage = err instanceof Error ? err.message : '测试连接时发生错误';
      toast.error('连接测试失败', {
        description: errorMessage,
      });
      
      const errorResult: ConnectionTestResponse = {
        success: false,
        message: errorMessage
      };
      
      setTestConnectionResult(errorResult);
      return errorResult;
    }
  };

  // 字段布局工具
  const field = formFieldLayout<{ value: any }>();

  return (
    <div className="space-y-4">
      <FormSectionsProvider>
        <SecondaryNavigatorLayout defaultValue="基础信息">
          <SecondaryNavigatorList>
            <SectionTabTrigger required value="基础信息" />
            <SectionTabTrigger required value="连接信息" />
            <SectionTabTrigger value="高级选项" />
            <Separator />
            
            <div className="py-2">
              <TestConnectionButton 
                onTest={handleTestConnection} 
                disabled={transitioning}
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
          </SecondaryNavigatorList>

          <GeneralSettingsForm<DatabaseConnectionUpdatePayload>
            data={{
              name: connection.name,
              description: connection.description,
              config: connection.config || {},
              read_only: connection.read_only,
              database_type: connection.database_type,
              test_connection: false
            }}
            readonly={false}
            loading={transitioning}
            onUpdate={(data, path) => handleUpdate(data as Partial<DatabaseConnectionUpdatePayload>, path as string[])}
          >
            {/* 基础信息 Section */}
            <Section title="基础信息">
              <SubSection title="基本信息">
                {/* 名称字段 */}
                <GeneralSettingsField accessor={nameAccessor} schema={nameSchema}>
                  <field.Basic label="连接名称" name="value">
                    <FormInput />
                  </field.Basic>
                </GeneralSettingsField>
                
                {/* 描述字段 */}
                <GeneralSettingsField accessor={descriptionAccessor} schema={descriptionSchema}>
                  <field.Basic label="描述 (可选)" name="value">
                    <Textarea 
                      className="min-h-[80px]"
                    />
                  </field.Basic>
                </GeneralSettingsField>
              </SubSection>
              
              <SubSection title="数据库类型">
                {/* 数据库类型 - 只读展示 */}
                <GeneralSettingsField 
                  accessor={fieldAccessor<DatabaseConnectionUpdatePayload, 'database_type'>('database_type')} 
                  schema={z.any()} 
                  readonly
                >
                  <field.Basic label="数据库类型" name="value">
                    <FormInput />
                  </field.Basic>
                </GeneralSettingsField>
              </SubSection>
            </Section>
            
            {/* 连接信息 Section */}
            <Section title="连接信息">
              <SubSection title="主机配置">
                {/* 主机字段 */}
                <GeneralSettingsField accessor={configAccessor('host')} schema={z.string().min(1, "主机不能为空")}>
                  <field.Basic label="主机 (Host)" name="value">
                    <FormInput />
                  </field.Basic>
                </GeneralSettingsField>
                
                {/* 端口字段 */}
                <GeneralSettingsField accessor={configAccessor('port')} schema={z.string()}>
                  <field.Basic label="端口 (Port)" name="value">
                    <FormInput type="number" />
                  </field.Basic>
                </GeneralSettingsField>
              </SubSection>
              
              <SubSection title="认证信息">
                {/* 用户字段 */}
                <GeneralSettingsField accessor={configAccessor('user')} schema={z.string().min(1, "用户名不能为空")}>
                  <field.Basic label="用户 (User)" name="value">
                    <FormInput />
                  </field.Basic>
                </GeneralSettingsField>
                
                {/* 使用密码开关 */}
                <GeneralSettingsField accessor={usePasswordAccessor} schema={z.boolean()}>
                  <field.Contained label="使用密码" name="value">
                    <FormSwitch />
                  </field.Contained>
                </GeneralSettingsField>
                
                {/* 密码字段 - 仅当使用密码时显示 */}
                {usePassword && (
                  <GeneralSettingsField 
                    accessor={passwordAccessor as GeneralSettingsFieldAccessor<DatabaseConnectionUpdatePayload, string | undefined>} 
                    schema={z.string().optional()}
                  >
                    <field.Basic 
                      label="密码 (Password)" 
                      name="value" 
                      description="输入以修改现有密码，留空则保持不变"
                    >
                      <FormInput 
                        type="password" 
                        placeholder="●●●●"
                      />
                    </field.Basic>
                  </GeneralSettingsField>
                )}
              </SubSection>
              
              <SubSection title="数据库名称">
                {/* 数据库名称字段 */}
                <GeneralSettingsField accessor={configAccessor('database')} schema={z.string().min(1, "数据库名称不能为空")}>
                  <field.Basic label="数据库名称 (Database)" name="value">
                    <FormInput />
                  </field.Basic>
                </GeneralSettingsField>
              </SubSection>
            </Section>
            
            {/* 高级选项 Section */}
            <Section title="高级选项">
              <SubSection title="访问模式">
                {/* 只读模式 */}
                <GeneralSettingsField accessor={readOnlyAccessor} schema={readOnlySchema}>
                  <field.Contained label="设置为只读模式" name="value" description="限制对数据库的写入操作，仅允许查询">
                    <FormSwitch />
                  </field.Contained>
                </GeneralSettingsField>
              </SubSection>
            </Section>
          </GeneralSettingsForm>
        </SecondaryNavigatorLayout>
      </FormSectionsProvider>
    </div>
  );
}

// Tab触发器组件 - 移除对useFormContext的依赖
function SectionTabTrigger({ value, required }: { value: string, required?: boolean }) {
  // 移除Form上下文相关代码
  // const [invalid, setInvalid] = useState(false);
  // const { form } = useFormContext();
  // const fields = useFormSectionFields(value);

  // useEffect(() => {
  //   return form.store.subscribe(() => {
  //     let invalid = false;
  //     for (let field of fields.values()) {
  //       if (field.getMeta().errors.length > 0) {
  //         invalid = true;
  //         break;
  //       }
  //     }
  //     setInvalid(invalid);
  //   });
  // }, [form, fields, value]);

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