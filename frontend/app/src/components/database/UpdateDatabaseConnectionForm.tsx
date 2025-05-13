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
import { PlusIcon, TrashIcon } from "lucide-react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";

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
  const [tableDescriptions, setTableDescriptions] = useState<Array<{ table: string; description: string }>>(
    connection.table_descriptions ? 
      Object.entries(connection.table_descriptions).map(([table, description]) => ({
        table,
        description: description as string
      })) : 
      []
  );
  const [columnDescriptions, setColumnDescriptions] = useState<Array<{ id: string; table: string; column: string; description: string }>>(
    connection.column_descriptions ? 
      Object.entries(connection.column_descriptions).reduce((arr, [key, desc]) => {
        const [table, column] = key.split('.');
        if (table && column) {
          arr.push({ id: crypto.randomUUID(), table, column, description: desc as string });
        }
        return arr;
      }, [] as Array<{ id: string; table: string; column: string; description: string }>) : 
      []
  );
  const [accessControl, setAccessControl] = useState<{ accessibleRoles: ('admin' | 'user')[] }>({ 
    accessibleRoles: (connection.accessible_roles as ('admin' | 'user')[]) || ['admin'] 
  });

  // 添加一个状态来跟踪当前正在编辑列描述的表
  const [currentEditingTable, setCurrentEditingTable] = useState<string | null>(null);

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

  const addTableDescription = () => {
    setTableDescriptions([...tableDescriptions, { table: '', description: '' }]);
  };

  const updateTableDescription = (index: number, field: 'table' | 'description', value: string) => {
    const newDescriptions = [...tableDescriptions];
    if (newDescriptions[index]) {
      newDescriptions[index][field] = value;
      setTableDescriptions(newDescriptions);
    }
  };

  const removeTableDescription = (index: number) => {
    setTableDescriptions(tableDescriptions.filter((_, i) => i !== index));
  };

  const handleUpdateTableDescriptions = async () => {
    try {
      // 转换为API需要的格式
      const tableDescs: Record<string, string> = {};
      tableDescriptions.forEach(item => {
        if (item.table && item.description) {
          tableDescs[item.table] = item.description;
        }
      });
      
      // 打印完整的请求负载以便调试
      const payload = {
        table_descriptions: tableDescs,
        test_connection: false
      };
      console.log("发送表描述更新请求:", JSON.stringify(payload));
      
      const result = await updateDatabaseConnection(connection.id, payload);
      
      // 打印响应以便调试
      console.log("表描述更新响应:", JSON.stringify(result));
      
      onUpdated(result);
      toast.success("表描述已更新");
    } catch (error) {
      console.error("更新表描述失败", error);
      toast.error("更新表描述失败: " + (error instanceof Error ? error.message : String(error)));
    }
  };

  const addColumnDescription = (tableName?: string) => {
    setColumnDescriptions([
      ...columnDescriptions, 
      { 
        id: crypto.randomUUID(),
        table: tableName || '', 
        column: '', 
        description: '' 
      }
    ]);
  };

  const updateColumnDescription = (index: number, field: 'table' | 'column' | 'description', value: string) => {
    const newDescriptions = [...columnDescriptions];
    if (newDescriptions[index]) {
      newDescriptions[index][field] = value;
      setColumnDescriptions(newDescriptions);
    }
  };

  const removeColumnDescription = (index: number) => {
    setColumnDescriptions(columnDescriptions.filter((_, i) => i !== index));
  };

  const handleUpdateColumnDescriptions = async () => {
    try {
      // 转换为API需要的格式
      const columnDescs: Record<string, string> = {};
      columnDescriptions.forEach(item => {
        if (item.table && item.column && item.description) {
          columnDescs[`${item.table}.${item.column}`] = item.description;
        }
      });
      
      // 打印完整的请求负载以便调试
      const payload = {
        column_descriptions: columnDescs,
        test_connection: false
      };
      console.log("发送列描述更新请求:", JSON.stringify(payload));
      
      const result = await updateDatabaseConnection(connection.id, payload);
      
      // 打印响应以便调试
      console.log("列描述更新响应:", JSON.stringify(result));
      
      onUpdated(result);
      toast.success("列描述已更新");
    } catch (error) {
      console.error("更新列描述失败", error);
      toast.error("更新列描述失败: " + (error instanceof Error ? error.message : String(error)));
    }
  };

  const handleUpdateAccessControl = async () => {
    try {
      // 打印完整的请求负载以便调试
      const payload = {
        accessible_roles: accessControl.accessibleRoles,
        test_connection: false
      };
      console.log("发送权限配置更新请求:", JSON.stringify(payload));
      
      const result = await updateDatabaseConnection(connection.id, payload);
      
      // 打印响应以便调试
      console.log("权限配置更新响应:", JSON.stringify(result));
      
      onUpdated(result);
      toast.success("权限配置已更新");
    } catch (error) {
      console.error("更新权限配置失败", error);
      toast.error("更新权限配置失败: " + (error instanceof Error ? error.message : String(error)));
    }
  };

  return (
    <div className="space-y-4">
      <FormSectionsProvider>
        <SecondaryNavigatorLayout defaultValue="基础信息">
          <SecondaryNavigatorList>
            <SectionTabTrigger required value="基础信息" />
            <SectionTabTrigger required value="连接信息" />
            <SectionTabTrigger value="高级选项" />
            <SectionTabTrigger value="表/列描述" />
            <SectionTabTrigger value="权限配置" />
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

            {/* 表/列描述 Section */}
            <Section title="表/列描述">
              {currentEditingTable === null ? (
                // 表描述界面
                <SubSection title="表描述">
                  <div className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                      添加表的业务描述，以便AI更好地理解数据模型，生成更准确的SQL查询。点击表旁边的"编辑列"按钮可以添加该表的列描述。
                    </p>
                    
                    {tableDescriptions.length > 0 && (
                      <div className="space-y-4 mt-4">
                        {tableDescriptions.map((item, index) => (
                          <div key={index} className="flex items-start gap-2">
                            <div className="flex-1">
                              <Label className="text-xs" htmlFor={`table-${index}`}>表名</Label>
                              <Input
                                id={`table-${index}`}
                                value={item.table}
                                onChange={(e) => updateTableDescription(index, 'table', e.target.value)}
                                className="mb-2"
                                placeholder="表名"
                              />
                            </div>
                            <div className="flex-[2]">
                              <Label className="text-xs" htmlFor={`table-desc-${index}`}>描述</Label>
                              <Input
                                id={`table-desc-${index}`}
                                value={item.description}
                                onChange={(e) => updateTableDescription(index, 'description', e.target.value)}
                                className="mb-2"
                                placeholder="表描述"
                              />
                            </div>
                            <div className="flex flex-col space-y-2 mt-6">
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={() => setCurrentEditingTable(item.table)}
                                disabled={!item.table}
                                className="whitespace-nowrap"
                              >
                                编辑列
                              </Button>
                            </div>
                            <div className="flex flex-col space-y-2 mt-6">
                            <Button
                                type="button"
                                variant="ghost"
                                size="icon"
                                onClick={() => removeTableDescription(index)}
                              >
                                <TrashIcon className="h-4 w-4" />
                              </Button>
                            </div>
                            
                          </div>
                        ))}
                      </div>
                    )}
                    
                    <div className="flex items-center justify-between">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={addTableDescription}
                        className="mt-2"
                      >
                        <PlusIcon className="h-4 w-4 mr-1" />
                        添加表描述
                      </Button>
                      
                      <Button
                        type="button"
                        onClick={handleUpdateTableDescriptions}
                        disabled={transitioning}
                        className="mt-2"
                      >
                        保存表描述
                      </Button>
                    </div>
                  </div>
                </SubSection>
              ) : (
                // 列描述界面
                <SubSection title={`${currentEditingTable} 表的列描述`}>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        添加 <strong>{currentEditingTable}</strong> 表中各列的业务描述，以便AI更好地理解数据字段的含义。
                      </p>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentEditingTable(null)}
                      >
                        返回表列表
                      </Button>
                    </div>
                    
                    {/* 过滤出当前表的列描述 */}
                    {(() => {
                      const tableColumns = columnDescriptions.filter(item => item.table === currentEditingTable);
                      return (
                        <>
                          {tableColumns.length > 0 && (
                            <div className="space-y-4 mt-4">
                              {tableColumns.map((item) => {
                                // 使用ID找到原始索引，而不是基于内容
                                const originalIndex = columnDescriptions.findIndex(
                                  desc => desc.id === item.id
                                );
                                
                                return (
                                  <div key={item.id} className="flex items-start gap-2">
                                    <div className="flex-1">
                                      <Label className="text-xs" htmlFor={`col-column-${item.id}`}>列名</Label>
                                      <Input
                                        id={`col-column-${item.id}`}
                                        value={item.column}
                                        onChange={(e) => updateColumnDescription(originalIndex, 'column', e.target.value)}
                                        className="mb-2"
                                        placeholder="列名"
                                      />
                                    </div>
                                    <div className="flex-[2]">
                                      <Label className="text-xs" htmlFor={`col-desc-${item.id}`}>描述</Label>
                                      <Input
                                        id={`col-desc-${item.id}`}
                                        value={item.description}
                                        onChange={(e) => updateColumnDescription(originalIndex, 'description', e.target.value)}
                                        className="mb-2"
                                        placeholder="列描述"
                                      />
                                    </div>
                                    <Button
                                      type="button"
                                      variant="ghost"
                                      size="icon"
                                      className="mt-6"
                                      onClick={() => removeColumnDescription(originalIndex)}
                                    >
                                      <TrashIcon className="h-4 w-4" />
                                    </Button>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                          
                          <div className="flex items-center justify-between mt-4">
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                addColumnDescription(currentEditingTable);
                              }}
                              className="mt-2"
                            >
                              <PlusIcon className="h-4 w-4 mr-1" />
                              添加列描述
                            </Button>
                            
                            <Button
                              type="button"
                              onClick={handleUpdateColumnDescriptions}
                              disabled={transitioning}
                              className="mt-2"
                            >
                              保存列描述
                            </Button>
                          </div>
                        </>
                      );
                    })()}
                  </div>
                </SubSection>
              )}
            </Section>
            
            {/* 权限配置 Section */}
            <Section title="权限配置">
              <SubSection title="可访问角色">
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    设置哪些角色可以访问此数据库连接。可以选择多个角色。
                  </p>
                  
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="role-admin" 
                        checked={accessControl.accessibleRoles.includes('admin')}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setAccessControl({
                              accessibleRoles: [...accessControl.accessibleRoles, 'admin']
                            });
                          } else {
                            setAccessControl({
                              accessibleRoles: accessControl.accessibleRoles.filter(role => role !== 'admin')
                            });
                          }
                        }}
                      />
                      <label
                        htmlFor="role-admin"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        超级管理员
                      </label>
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">
                      超级管理员可以执行任何查询操作
                    </p>
                    
                    <div className="flex items-center space-x-2">
                      <Checkbox 
                        id="role-user" 
                        checked={accessControl.accessibleRoles.includes('user')}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setAccessControl({
                              accessibleRoles: [...accessControl.accessibleRoles, 'user']
                            });
                          } else {
                            setAccessControl({
                              accessibleRoles: accessControl.accessibleRoles.filter(role => role !== 'user')
                            });
                          }
                        }}
                      />
                      <label
                        htmlFor="role-user"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                      >
                        普通用户
                      </label>
                    </div>
                    <p className="text-xs text-muted-foreground ml-6">
                      普通用户只能执行查询操作
                    </p>
                  </div>
                  
                  <Button
                    type="button"
                    onClick={handleUpdateAccessControl}
                    disabled={transitioning || accessControl.accessibleRoles.length === 0}
                    className="mt-4"
                  >
                    保存权限配置
                  </Button>
                </div>
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