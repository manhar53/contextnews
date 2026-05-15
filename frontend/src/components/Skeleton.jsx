export function CardSkeleton() {
  return (
    <div className="bg-surface border border-border rounded-xl p-4 animate-pulse">
      <div className="flex justify-between gap-3 mb-3">
        <div className="h-4 bg-surface2 rounded w-3/4" />
        <div className="h-4 bg-surface2 rounded w-16" />
      </div>
      <div className="h-3 bg-surface2 rounded w-full mb-2" />
      <div className="h-3 bg-surface2 rounded w-2/3 mb-4" />
      <div className="h-3 bg-surface2 rounded w-1/3" />
    </div>
  );
}

export function DetailSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-5 py-6 animate-pulse">
      <div className="h-3 bg-surface2 rounded w-24 mb-6" />
      <div className="h-7 bg-surface2 rounded w-5/6 mb-3" />
      <div className="h-3 bg-surface2 rounded w-1/3 mb-8" />
      <div className="h-24 bg-surface rounded-xl mb-8" />
      <div className="flex gap-3 mb-8">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="h-28 bg-surface rounded-xl flex-1" />
        ))}
      </div>
      <div className="h-32 bg-surface rounded-xl" />
    </div>
  );
}
