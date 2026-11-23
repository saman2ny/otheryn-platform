import type { ReactNode } from 'react';

type HeroShellProps = {
  children: ReactNode;
  background?: ReactNode;
  card?: boolean;
  className?: string;
  contentClassName?: string;
};

export default function HeroShell({
  children,
  background,
  card = false,
  className = '',
  contentClassName = '',
}: HeroShellProps) {
  return (
    <section
      className={`relative mt-20 border-b border-ink/15 p-5 sm:p-8 lg:p-12 ${className}`}
    >
      {background}
      <div
        className={`relative mx-auto w-full ${
          card ? 'spatial-surface p-5 sm:p-8 lg:p-12' : ''
        } ${contentClassName}`}
      >
        {children}
      </div>
    </section>
  );
}