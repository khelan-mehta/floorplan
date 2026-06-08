import { type ReactNode } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { cn } from './cn';

/** Resizable split layout. `direction` horizontal = side-by-side panes. */
export function Split({
  direction = 'horizontal',
  children,
  className,
}: {
  direction?: 'horizontal' | 'vertical';
  children: ReactNode;
  className?: string;
}) {
  return (
    <PanelGroup direction={direction} className={cn('h-full w-full', className)}>
      {children}
    </PanelGroup>
  );
}

export function SplitPane({
  children,
  defaultSize,
  minSize,
  className,
}: {
  children: ReactNode;
  defaultSize?: number;
  minSize?: number;
  className?: string;
}) {
  return (
    <Panel defaultSize={defaultSize} minSize={minSize} className={cn('h-full', className)}>
      {children}
    </Panel>
  );
}

export function SplitHandle({
  direction = 'horizontal',
}: {
  direction?: 'horizontal' | 'vertical';
}) {
  return (
    <PanelResizeHandle
      className={cn(
        'bg-line transition-colors hover:bg-accent',
        direction === 'horizontal' ? 'w-1' : 'h-1',
      )}
    />
  );
}
