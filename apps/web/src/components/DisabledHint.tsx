import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

type DisabledHintProviderProps = {
  children: ReactNode;
};

export default function DisabledHintProvider({ children }: DisabledHintProviderProps) {
  const [message, setMessage] = useState('');
  const [visible, setVisible] = useState(false);
  const timeout = useRef<number | null>(null);

  const clear = useCallback(() => {
    if (timeout.current !== null) {
      window.clearTimeout(timeout.current);
      timeout.current = null;
    }
  }, []);

  const hide = useCallback(() => {
    clear();
    setVisible(false);
  }, [clear]);

  const show = useCallback(
    (value: string) => {
      clear();
      setMessage(value);
      setVisible(true);
      timeout.current = window.setTimeout(() => {
        setVisible(false);
        timeout.current = null;
      }, 4000);
    },
    [clear],
  );

  useEffect(() => {
    const findHint = (target: EventTarget | null) =>
      target instanceof Element ? target.closest<HTMLElement>('[data-disabled-hint]') : null;

    const handleOver = (event: MouseEvent) => {
      const hint = findHint(event.target);
      if (hint?.dataset.disabledHint) show(hint.dataset.disabledHint);
    };

    const handleOut = (event: MouseEvent) => {
      const hint = findHint(event.target);
      const related =
        event.relatedTarget instanceof Element
          ? event.relatedTarget.closest('[data-disabled-hint]')
          : null;
      if (hint && hint !== related) hide();
    };

    const handleFocus = (event: FocusEvent) => {
      const hint = findHint(event.target);
      if (hint?.dataset.disabledHint) show(hint.dataset.disabledHint);
    };

    const handleBlur = (event: FocusEvent) => {
      const hint = findHint(event.target);
      const related =
        event.relatedTarget instanceof Element
          ? event.relatedTarget.closest('[data-disabled-hint]')
          : null;
      if (hint && hint !== related) hide();
    };

    const handleClick = (event: MouseEvent) => {
      const hint = findHint(event.target);
      if (hint?.dataset.disabledHint) show(hint.dataset.disabledHint);
    };

    document.addEventListener('mouseover', handleOver);
    document.addEventListener('mouseout', handleOut);
    document.addEventListener('focusin', handleFocus);
    document.addEventListener('focusout', handleBlur);
    document.addEventListener('click', handleClick);

    return () => {
      document.removeEventListener('mouseover', handleOver);
      document.removeEventListener('mouseout', handleOut);
      document.removeEventListener('focusin', handleFocus);
      document.removeEventListener('focusout', handleBlur);
      document.removeEventListener('click', handleClick);
    };
  }, [show, hide]);

  useEffect(() => () => clear(), [clear]);

  return (
    <>
      {children}
      {createPortal(
        <div
          role="status"
          aria-live="polite"
          className={`pointer-events-none fixed bottom-6 left-1/2 z-[60] w-[calc(100%-2rem)] max-w-md -translate-x-1/2 transition-all duration-200 ${
            visible ? 'translate-y-0 opacity-100' : 'translate-y-2 opacity-0'
          }`}
        >
          <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-forest px-4 py-3 text-sm leading-6 text-paper shadow-[0_24px_60px_-20px_rgba(0,0,0,0.55)]">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-citrus" />
            <span>{message}</span>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}