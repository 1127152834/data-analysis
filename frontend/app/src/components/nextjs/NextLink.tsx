'use client';

import { type ButtonProps, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import Link, { type LinkProps } from 'next/link';
import { useRouter } from 'next/navigation';
import { forwardRef, MouseEvent, useTransition, AnchorHTMLAttributes } from 'react';

export interface NextLinkProps extends
  // Pick relevant LinkProps, excluding href, children, and props handled by ButtonProps or AnchorHTMLAttributes
  Pick<LinkProps, 'prefetch' | 'scroll' | 'replace' | 'as' | 'passHref' | 'legacyBehavior' | 'locale' | 'onClick'>,
  // Pick ButtonProps for styling and base interaction
  Pick<ButtonProps, 'className' | 'style' | 'variant' | 'size' | 'disabled' | 'children'>,
  // Allow other standard anchor attributes, omitting those explicitly handled or conflicting
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, 'href' | 'onClick' | 'className' | 'style' | 'children' | 'type'>
{
  href: string; // Explicitly define href as string for router methods
}

export const NextLink = forwardRef<HTMLAnchorElement, NextLinkProps>(({ 
  className, 
  disabled: propDisabled, 
  onClick, 
  href, // Now a string
  replace, 
  scroll, 
  variant, 
  size, 
  children,
  prefetch,
  as,
  passHref,
  legacyBehavior,
  locale,
  ...props // other props like 'title', 'target' will be in here
}, ref) => {
  const [navigating, startTransition] = useTransition();
  const router = useRouter();

  const disabled = navigating || !!propDisabled;

  const handleClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (disabled) {
      event.preventDefault();
      return;
    }
    // For new tab/window or special key combinations, let the browser handle it.
    if (event.ctrlKey || event.shiftKey || event.metaKey || event.altKey) {
      // onClick?.(event); // Optionally call onClick if specific handling for these cases is needed
      return;
    }
    
    onClick?.(event); // Call the passed onClick handler

    if (event.defaultPrevented) {
      return; // If onClick prevented default, respect that
    }

    event.preventDefault(); // Prevent default browser navigation

    startTransition(() => {
      if (replace) {
        router.replace(href, { scroll }); // href is a string
      } else {
        router.push(href, { scroll });   // href is a string
      }
    });
  };

  return (
    <Link
      href={href} // Pass the string href
      onClick={handleClick} // Use our custom click handler
      className={cn(
        buttonVariants({ variant, size }), 
        'aria-disabled:pointer-events-none aria-disabled:opacity-50', 
        navigating && '!cursor-wait',
        className
      )}
      replace={replace}
      scroll={scroll}
      prefetch={prefetch}
      as={as}
      passHref={passHref}
      legacyBehavior={legacyBehavior}
      locale={locale}
      aria-disabled={disabled}
      ref={ref}
      role="button" // For accessibility if styled as a button
      {...props} // Pass all other props like title, target, etc.
    >
      {children} {/* Pass children to the Link component */}
    </Link>
  );
});

NextLink.displayName = 'NextLink';