'use client';

import { logout } from '@/api/auth';
import { useAuth } from '@/components/auth/AuthProvider';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { useHref } from '@/components/use-href';
import { LogInIcon } from 'lucide-react';
import NextLink from 'next/link';
import { useRouter } from 'next/navigation';

export function NavFooter() {
  const href = useHref();
  const user = useAuth().me;
  const router = useRouter();

  if (!user) {
    return (
      <Button variant="ghost" asChild>
        <NextLink href={`/auth/login?callbackUrl=${encodeURIComponent(href)}`} prefetch={false} className="items-center w-full gap-2">
          <LogInIcon size="1em" />
          登录
        </NextLink>
      </Button>
    );
  }
  return (
    <div className="flex items-center gap-2">
      <DropdownMenu>
        <DropdownMenuTrigger>
          <Avatar className="border dark:bg-primary bg-primary-foreground p-0.5 w-8 h-8">
            <AvatarFallback className="text-xs">
              {user.email.slice(0, 2)}
            </AvatarFallback>
          </Avatar>
        </DropdownMenuTrigger>
        <DropdownMenuContent collisionPadding={8} side="top">
          <DropdownMenuItem onClick={() => {
            logout().finally(() => {
              router.refresh();
            });
          }}>
            退出登录
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <span className="text-sm font-semibold">
        {user.email}
      </span>
    </div>
  );
} 