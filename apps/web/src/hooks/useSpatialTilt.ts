import { useRef, type PointerEvent } from 'react';

export default function useSpatialTilt(maxTilt = 5) {
  const ref = useRef<HTMLDivElement>(null);

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (event.pointerType !== 'mouse') return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const element = ref.current;
    if (!element) return;

    const rect = element.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width - 0.5;
    const y = (event.clientY - rect.top) / rect.height - 0.5;

    element.style.transform = `perspective(1400px) rotateX(${(-y * maxTilt).toFixed(
      2,
    )}deg) rotateY(${(x * maxTilt).toFixed(2)}deg) translateY(-4px)`;
  };

  const handlePointerLeave = () => {
    if (ref.current) ref.current.style.transform = '';
  };

  return { ref, handlePointerMove, handlePointerLeave };
}