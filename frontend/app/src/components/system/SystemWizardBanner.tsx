'use client';

import { isBootstrapStatusPassed } from '@/api/system';
import { useBootstrapStatus } from './BootstrapStatusProvider';

export function SystemWizardBanner () {
  const bootstrapStatus = useBootstrapStatus();
  const configured = isBootstrapStatusPassed(bootstrapStatus);

  if (!configured) {
    return (
      <div className="absolute left-0 top-0 w-full p-1 text-xs text-center bg-warning/10 text-warning">
        此站点尚未准备就绪。请登录或联系管理员完成设置配置。
      </div>
    );
  }
}
