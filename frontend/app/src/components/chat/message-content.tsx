import { useChatMessageField } from '@/components/chat/chat-hooks';
import { ChatMessageController } from '@/components/chat/chat-message-controller';
import { RemarkContent } from '@/components/remark-content';
import { DatabaseQueryResult } from '@/components/database-query';

export function MessageContent ({ message }: { message: ChatMessageController | undefined }) {
  const content = useChatMessageField(message, 'content') ?? '';
  // 检查消息是否包含数据库查询结果
  const dbQuery = useChatMessageField(message, 'database_query');
  
  return (
    <>
      <RemarkContent>
        {content}
      </RemarkContent>
      
      {dbQuery && dbQuery.result && (
        <DatabaseQueryResult
          query={dbQuery.query}
          result={{
            columns: dbQuery.result.columns || [],
            rows: dbQuery.result.rows || [],
            totalRows: dbQuery.result.total_rows || dbQuery.result.rows?.length || 0,
            executionTimeMs: dbQuery.execution_time_ms || 0
          }}
          connectionName={dbQuery.connection_name}
          databaseType={dbQuery.database_type}
          error={dbQuery.error}
          className="mt-4"
        />
      )}
    </>
  );
}
