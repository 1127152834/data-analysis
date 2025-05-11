import { ThemeToggle } from '@/components/theme-toggle';
import clsx from 'clsx';

export type SiteSocialsType = {
  github?: string | null;
  twitter?: string | null;
  discord?: string | null;
};

export function SiteHeaderActions (props: {
  className?: string;
  social?: SiteSocialsType;
}) {
  const { className, social = {} } = props;
  return (
    <div className={clsx('h-header w-full gap-0.5 items-center', className)}>
      <ThemeToggle />
    </div>
  );
}
