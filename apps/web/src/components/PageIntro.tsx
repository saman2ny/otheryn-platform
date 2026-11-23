import type { ReactNode } from 'react';
import HeroShell from './HeroShell';

type PageIntroProps = {
  index: string;
  eyebrow: string;
  title: ReactNode;
  children: ReactNode;
};

export default function PageIntro({ index, eyebrow, title, children }: PageIntroProps) {
  return (
    <HeroShell card className="bg-paper">
      <div className="grid gap-10 lg:grid-cols-[1.3fr_0.7fr] lg:items-end">
        <div>
          <div className="mb-6 flex items-center gap-3">
            <span className="font-mono text-[0.65rem] text-clay">{index}</span>
            <span className="h-px w-8 bg-ink/25" />
            <p className="eyebrow">{eyebrow}</p>
          </div>
          <h1 className="max-w-5xl font-display text-[clamp(3.3rem,7vw,7rem)] leading-[0.88] tracking-[-0.06em] text-ink">
            {title}
          </h1>
        </div>
        <div className="max-w-md lg:justify-self-end lg:pb-2">
          <div className="spatial-inset p-5">
            <p className="eyebrow mb-3">Overview</p>
            <p className="text-base leading-7 text-ink/65">{children}</p>
          </div>
        </div>
      </div>
    </HeroShell>
  );
}