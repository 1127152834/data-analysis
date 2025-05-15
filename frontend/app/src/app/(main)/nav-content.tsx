'use client';

import { useAuth } from '@/components/auth/AuthProvider';
import { ChatNewDialog } from '@/components/chat/chat-new-dialog';
import { ChatsHistory } from '@/components/chat/chats-history';
import { useAllKnowledgeBases } from '@/components/knowledge-base/hooks';
import { useAllChatEngines } from '@/components/chat-engine/hooks';
import { type NavGroup, SiteNav } from '@/components/site-nav';
import { useBootstrapStatus } from '@/components/system/BootstrapStatusProvider';
import { Skeleton } from '@/components/ui/skeleton';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { useHref } from '@/components/use-href';
import { ActivitySquareIcon, AlertTriangleIcon, BinaryIcon, BotMessageSquareIcon, BrainCircuitIcon, CircleDotIcon, CogIcon, ComponentIcon, DatabaseIcon, FileLineChart, HomeIcon, KeyRoundIcon, LibraryBigIcon, LibraryIcon, MessageCircleQuestionIcon, MessagesSquareIcon, ShuffleIcon } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';

export function NavContent() {
  const { required, need_migration } = useBootstrapStatus();
  const href = useHref();
  const auth = useAuth();
  const user = auth.me;
  const isLoggedIn = !!user;

  const disableIfNotAuthenticated = !isLoggedIn ? <><Link className="font-semibold underline" href={`/auth/login?callbackUrl=${encodeURIComponent(href)}`}>登录</Link> 以继续</> : false;

  const groups: NavGroup[] = [
    {
      items: [
        { custom: true, key: 'new-chat', children: <ChatNewDialog /> },
        { href: '/', title: '首页', icon: HomeIcon, exact: true },
        { href: '/c', title: '会话记录', exact: true, icon: MessagesSquareIcon, disabled: disableIfNotAuthenticated },
        { custom: true, key: 'history', children: <ChatsHistory /> },
      ],
    },
  ];

  if (user?.is_superuser) {
    groups.push({
      title: '管理',
      items: [
        { href: '/stats/trending', title: '仪表盘', icon: ActivitySquareIcon },
        {
          href: '/knowledge-bases',
          title: '知识库',
          icon: LibraryBigIcon,
          details: !required.knowledge_base
            ? <NavWarningDetails>您需要配置至少一个知识库。</NavWarningDetails>
            : <KnowledgeBaseNavDetails />,
        },
        {
          href: '/chat-engines',
          title: '聊天引擎',
          icon: BotMessageSquareIcon,
          details: !!need_migration.chat_engines_without_kb_configured?.length
            ? <NavWarningDetails>
              一些聊天引擎需要<a href="/releases/0.3.0#manual-migration" className="underline">配置知识库</a>。
            </NavWarningDetails>
            : !required.default_chat_engine
              ? <NavWarningDetails>您需要配置默认聊天引擎。</NavWarningDetails>
              : <ChatEnginesNavDetails />,
        },
        {
          parent: true,
          key: 'models',
          title: '模型',
          icon: ComponentIcon,
          details: (!required.default_llm || !required.default_embedding_model) && <NavWarningDetails />,
          children: [
            { href: '/llms', title: '大语言模型', icon: BrainCircuitIcon, details: !required.default_llm ? <NavWarningDetails>您需要配置至少一个默认大语言模型。</NavWarningDetails> : undefined },
            { href: '/embedding-models', title: '嵌入模型', icon: BinaryIcon, details: !required.default_embedding_model && <NavWarningDetails>您需要配置至少一个默认嵌入模型。</NavWarningDetails> },
            { href: '/reranker-models', title: '重排序模型', icon: ShuffleIcon },
          ],
        },
        { href: '/database', title: '数据库管理', icon: DatabaseIcon },
        { href: '/feedbacks', title: '反馈', icon: MessageCircleQuestionIcon },
        {
          parent: true,
          key: 'evaluation',
          title: '评估',
          icon: FileLineChart,
          children: [
            { href: '/evaluation/tasks', title: '任务', icon: CircleDotIcon },
            { href: '/evaluation/datasets', title: '数据集', icon: LibraryIcon },
          ],
        },
        { href: '/site-settings', title: '设置', icon: CogIcon },
      ],
      sectionProps: { className: 'mt-auto mb-0' },
    });
  }

  if (user?.is_superuser) {
    groups.push({
      title: '账户',
      items: [
        { href: '/api-keys', title: 'API密钥', icon: KeyRoundIcon },
      ],
    });
  }

  return (
    <SiteNav groups={groups} />
  );
}

function NavWarningDetails({ children }: { children?: ReactNode }) {
  if (!children) {
    return <AlertTriangleIcon className="text-warning size-4" />;
  }
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <AlertTriangleIcon className="text-warning size-4" />
        </TooltipTrigger>
        <TooltipContent>
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function CountSpan({ children }: { children?: ReactNode }) {
  return <span className="text-xs opacity-50 font-normal inline-block mr-1">{children}</span>;
}

function KnowledgeBaseNavDetails() {
  const { data: knowledgeBases, isLoading } = useAllKnowledgeBases();

  if (isLoading) {
    return <Skeleton className="flex-shrink-0 w-6 h-4" />;
  }

  return <CountSpan>{knowledgeBases?.length}</CountSpan>;
}

function ChatEnginesNavDetails() {
  const { data, isLoading } = useAllChatEngines();

  if (isLoading) {
    return <Skeleton className="flex-shrink-0 w-6 h-4" />;
  }

  return <CountSpan>{data?.length}</CountSpan>;
} 