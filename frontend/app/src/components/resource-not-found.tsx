import { NextLink } from '@/components/nextjs/NextLink';
import type { ReactNode } from 'react';

export function ResourceNotFound ({
  resource,
  buttonContent = '返回',
  buttonHref = '/',
}: {
  resource: string,
  buttonContent?: ReactNode,
  buttonHref?: string,
}) {
  return (
    <div className="flex items-center h-full px-4 py-12 sm:px-6 md:px-8 lg:px-12 xl:px-16">
      <div className="w-full space-y-6 text-center">
        <div className="space-y-3">
          <h2 className="text-4xl sm:text-2xl">
            <span className="tracking-tighter text-muted-foreground">
              {'404 '}
            </span>
            <span className="font-bold">
              {resource}
            </span>
            <span className="tracking-tighter text-muted-foreground">
              {' 未找到'}
            </span>
          </h2>
          <p className="text-muted-foreground text-sm">
            看起来您进入了未知的数字领域。
          </p>
        </div>
        <NextLink href={buttonHref}>
          {buttonContent}
        </NextLink>
      </div>
    </div>
  );
}