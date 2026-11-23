import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import { bookingProviderOptions } from '../lib/validation';

type ProvidersSelectProps = {
  value: string;
  onChange: (value: string) => void;
  error?: boolean;
};

export default function ProvidersSelect({ value, onChange, error = false }: ProvidersSelectProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const listboxId = useId();

  const options = bookingProviderOptions.map((option) => ({ value: option, label: option }));

  useEffect(() => {
    if (!open) return;

    const handlePointerDown = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [open]);

  const focusOption = (index: number) => {
    optionRefs.current[index]?.focus();
  };

  const openAndFocus = (index: number) => {
    setOpen(true);
    window.setTimeout(() => focusOption(index), 0);
  };

  const close = (focusTrigger = false) => {
    setOpen(false);
    if (focusTrigger) window.setTimeout(() => triggerRef.current?.focus(), 0);
  };

  const handleTriggerKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      openAndFocus(event.key === 'ArrowDown' ? 0 : options.length - 1);
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (open) close(true);
      else openAndFocus(0);
      return;
    }

    if (event.key === 'Escape') {
      close(true);
    }
  };

  const handleListboxKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const current = optionRefs.current.findIndex((option) => option === document.activeElement);

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusOption(Math.min(current + 1, options.length - 1));
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusOption(Math.max(current - 1, 0));
      return;
    }

    if (event.key === 'Home') {
      event.preventDefault();
      focusOption(0);
      return;
    }

    if (event.key === 'End') {
      event.preventDefault();
      focusOption(options.length - 1);
      return;
    }

    if (event.key === 'Escape') {
      event.preventDefault();
      close(true);
      return;
    }

    if (event.key === 'Tab') {
      close(false);
    }
  };

  const selectOption = (index: number) => {
    onChange(options[index].value);
    close(true);
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        id="providers"
        type="button"
        className={`mt-2 flex w-full items-center justify-between gap-3 rounded-xl border bg-white/60 px-4 py-3 text-left text-ink backdrop-blur-md transition hover:border-ink/35 focus:border-forest/60 focus:outline-none focus:ring-2 focus:ring-forest/20 ${
          error ? 'border-clay/70 focus:border-clay focus:ring-clay/20' : 'border-ink/20'
        }`}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-labelledby="providers-label"
        aria-invalid={error}
        aria-describedby={error ? 'providers-error' : undefined}
        onClick={() => {
          if (open) close(true);
          else openAndFocus(0);
        }}
        onKeyDown={handleTriggerKeyDown}
      >
        <span className={`min-w-0 truncate ${value ? 'text-ink' : 'text-ink/50'}`}>
          {value || 'Select number of providers'}
        </span>
        <span className="flex shrink-0 items-center gap-2">
          {value && <span className="h-1.5 w-1.5 rounded-full bg-forest" />}
          <svg
            className={`h-4 w-4 text-ink/50 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.7} d="m6 9 6 6 6-6" />
          </svg>
        </span>
      </button>

      {open && (
        <div
          id={listboxId}
          role="listbox"
          aria-labelledby="providers-label"
          className="absolute z-50 mt-2 w-full rounded-xl border border-white/60 bg-bone/95 shadow-[0_30px_90px_-20px_rgba(23,37,31,0.45)] backdrop-blur-2xl"
          onKeyDown={handleListboxKeyDown}
        >
          <div className="p-1">
            {options.map((option, index) => (
              <button
                key={option.value}
                ref={(node) => {
                  optionRefs.current[index] = node;
                }}
                type="button"
                role="option"
                aria-selected={value === option.value}
                tabIndex={-1}
                onClick={() => selectOption(index)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault();
                    selectOption(index);
                  }
                }}
                className={`flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left text-sm transition ${
                  value === option.value
                    ? 'bg-forest text-paper'
                    : 'text-ink hover:bg-moss/50'
                }`}
              >
                <span className="flex items-center gap-2">
                  {value === option.value && <span className="h-1.5 w-1.5 rounded-full bg-citrus" />}
                  {option.label}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}