import { useChatMessageField, useChatMessageStreamContainsState } from '@/components/chat/chat-hooks';
import type { ChatMessageController } from '@/components/chat/chat-message-controller';
import { AppChatStreamState } from '@/components/chat/chat-stream-state';
import { MessageBetaAlert } from '@/components/chat/message-beta-alert';
import { MessageContent } from '@/components/chat/message-content';
import { DatabaseIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

export function MessageAnswer ({ message, showBetaAlert }: { message: ChatMessageController | undefined, showBetaAlert?: boolean }) {
  const content = useChatMessageField(message, 'content');
  const shouldShow = useChatMessageStreamContainsState(message, AppChatStreamState.GENERATE_ANSWER);
  const dbQuery = useChatMessageField(message, 'database_query');
  const hasDatabaseQuery = !!dbQuery;

  if (!shouldShow && !content?.length) {
    return null;
  }

  return (
    <>
      <div className="font-normal text-lg flex items-center gap-2">
        <svg className="dark:hidden size-4" viewBox="0 0 745 745" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="12" y="12" width="721" height="721" rx="108" stroke="#212121" strokeWidth="24" />
          <rect x="298" y="172" width="150" height="150" rx="24" fill="#212121" />
          <rect x="298" y="422" width="150" height="150" rx="24" fill="#212121" />
        </svg>
        <svg className="hidden dark:block size-4" viewBox="0 0 745 745" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="12" y="12" width="721" height="721" rx="108" stroke="white" strokeWidth="24" />
          <rect x="298" y="172" width="150" height="150" rx="24" fill="white" />
          <rect x="298" y="422" width="150" height="150" rx="24" fill="white" />
        </svg>
        回答
        {hasDatabaseQuery && (
          <span className={cn(
            "flex items-center text-sm px-2 py-0.5 rounded-full",
            dbQuery?.error ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" : "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
          )}>
            <DatabaseIcon size={14} className="mr-1" />
            {dbQuery?.error ? "查询错误" : "数据库查询"}
          </span>
        )}
      </div>
      {showBetaAlert && <MessageBetaAlert />}
      <MessageContent message={message} />
    </>
  );
}