import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog';
import { Button, type ButtonProps, buttonVariants } from '@/components/ui/button';
import { getErrorMessage } from '@/lib/errors';
import { cn } from '@/lib/utils';
import { AlertTriangleIcon, Loader2Icon } from 'lucide-react';
import { forwardRef, MouseEvent, type ReactNode, useState } from 'react';

export interface DangerousActionButtonProps extends ButtonProps {
  action: () => Promise<void>;
  dialogTitle?: ReactNode;
  dialogDescription?: ReactNode;
  actionDisabled?: boolean;
  actionDisabledReason?: ReactNode;
}

export const DangerousActionButton = forwardRef<HTMLButtonElement, DangerousActionButtonProps>(({ action, dialogDescription, dialogTitle, actionDisabledReason, actionDisabled, asChild, ...props }, ref) => {
  const [open, setOpen] = useState(false);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<unknown>();

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault();
    setActing(true);
    action()
      .then(() => {
        setOpen(false);
      })
      .catch(error => setError(error))
      .finally(() => setActing(false));
  };

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      {asChild
        ? <AlertDialogTrigger asChild ref={ref} {...props} disabled={props.disabled || acting} />
        : (
          <AlertDialogTrigger asChild>
            <Button variant="destructive" ref={ref} {...props} disabled={props.disabled || acting} />
          </AlertDialogTrigger>
        )}
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{dialogTitle ?? '您确定要执行此操作吗？'}</AlertDialogTitle>
          <AlertDialogDescription>
            {dialogDescription ?? '此操作无法撤销。'}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {!!error && <Alert variant="destructive" className={cn('transition-opacity', acting && 'opacity-50')}>
          <AlertTriangleIcon />
          <AlertTitle>操作失败</AlertTitle>
          <AlertDescription>{getErrorMessage(error)}</AlertDescription>
        </Alert>}
        {actionDisabled && actionDisabledReason}
        <AlertDialogFooter>
          <AlertDialogCancel className={cn('border-none', buttonVariants({ variant: 'ghost' }))}>取消</AlertDialogCancel>
          <AlertDialogAction className={buttonVariants({ variant: 'destructive' })} disabled={actionDisabled || acting} onClick={handleClick}>
            {acting && <Loader2Icon className="size-4 mr-1 animate-spin repeat-infinite" />}
            继续
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
});

DangerousActionButton.displayName = 'DangerousActionButton';
