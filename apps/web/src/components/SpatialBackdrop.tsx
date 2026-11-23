export default function SpatialBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_-10%,rgba(255,255,255,0.85),transparent_55%)]" />
      <div className="animate-spatial-drift absolute -left-40 top-[-8rem] h-[32rem] w-[32rem] rounded-full bg-citrus/30 blur-3xl" />
      <div className="animate-spatial-float absolute right-[-12rem] top-[18rem] h-[36rem] w-[36rem] rounded-full bg-forest/20 blur-3xl" />
      <div className="absolute bottom-[-10rem] left-[28%] h-[28rem] w-[28rem] rounded-full bg-clay/20 blur-3xl" />
      <div className="spatial-grid absolute inset-0 opacity-45" />
      <div className="absolute inset-3 rounded-[2rem] border border-white/35" />
      <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(242,239,231,0)_0%,rgba(242,239,231,0.65)_100%)]" />
    </div>
  );
}