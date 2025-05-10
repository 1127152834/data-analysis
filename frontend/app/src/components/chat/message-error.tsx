import { useChatMessageField, useChatMessageStreamState } from '@/components/chat/chat-hooks';
import { ChatMessageController } from '@/components/chat/chat-message-controller';
import { AppChatStreamState } from '@/components/chat/chat-stream-state';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { format } from 'date-fns';

export function MessageError ({ message }: { message: ChatMessageController }) {
  const messageError = useChatMessageField(message, 'error');
  const ongoing = useChatMessageStreamState(message);

  let variant: 'destructive' | 'warning' = 'destructive';
  let errorTitle = '生成回复失败';
  let error: string | undefined;

  if (messageError) {
    error = messageError;
  } else if (ongoing?.state === AppChatStreamState.UNKNOWN) {
    variant = 'warning';
    errorTitle = '无法访问消息内容';
    error = `此消息尚未完成或意外终止。(创建于 ${format(message.message.created_at, 'yyyy-MM-dd HH:mm:ss')})`;
  }

  if (error) {
    return (
      <Alert variant={variant}>
        <AlertTitle>{errorTitle}</AlertTitle>
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  } else {
    return null;
  }
}
