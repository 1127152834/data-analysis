import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { FlaskConicalIcon } from 'lucide-react';

export function MessageBetaAlert () {
  return (
    <Alert variant="info" className='my-2'>
      <FlaskConicalIcon />
      <AlertTitle>
        该聊天机器人处于Beta阶段。
      </AlertTitle>
      <AlertDescription>
        所有生成的信息在使用前应进行验证。
      </AlertDescription>
    </Alert>
  );
}
